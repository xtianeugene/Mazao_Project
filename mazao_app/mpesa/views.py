from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django_daraja.mpesa.core import MpesaClient
from django.contrib import messages
from django.urls import reverse  # Add this import
import json
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

# Initialize M-Pesa client (global instance)
cl = MpesaClient()


def index(request):
    """
    Home page with payment form
    """
    return render(request, 'mpesa/index.html')


def initiate_payment(request):
    """
    Initiate M-Pesa STK Push payment
    """
    if request.method == 'POST':
        try:
            # Get form data
            phone_number = request.POST.get('phone_number')
            amount = request.POST.get('amount')
            account_reference = request.POST.get('account_reference', 'PAYMENT')
            transaction_desc = request.POST.get('transaction_desc', 'Payment for services')

            # Validate inputs
            if not phone_number:
                messages.error(request, "Phone number is required!")
                return redirect('mpesa:index')

            if not amount:
                messages.error(request, "Amount is required!")
                return redirect('mpesa:index')

            # Format phone number
            formatted_phone = format_phone_number(phone_number)
            if not formatted_phone:
                messages.error(request, "Invalid phone number format! Use 07XXXXXXXX or 2547XXXXXXXX")
                return redirect('mpesa:index')

            # Convert amount to integer
            try:
                amount_int = int(float(amount))
                if amount_int < 1:
                    messages.error(request, "Amount must be at least 1 KSH")
                    return redirect('mpesa:index')
            except ValueError:
                messages.error(request, "Invalid amount entered!")
                return redirect('mpesa:index')

            # Get callback URL
            callback_url ="https://mydomain.com/mpesa-express-simulate/"

            # DEBUG: Print callback URL
            logger.info(f"Callback URL: {callback_url}")
            logger.info(f"Phone: {formatted_phone}, Amount: {amount_int}")

            # FIX: Try different approach for stk_push
            try:
                # Method 1: Try the standard way
                response = cl.stk_push(
                    phone_number=formatted_phone,
                    amount=amount_int,
                    account_reference=account_reference,
                    transaction_desc=transaction_desc,
                    callback_url=callback_url
                )

                # DEBUG: Print response type and content
                logger.info(f"Response type: {type(response)}")
                logger.info(f"Response: {response}")

                # Convert response based on its type
                if hasattr(response, 'text'):
                    # It's a requests Response object
                    response_text = response.text
                    logger.info(f"Response text: {response_text}")
                    response_data = json.loads(response_text)
                elif hasattr(response, '__dict__'):
                    # It's an object with __dict__
                    response_data = response.__dict__
                    logger.info(f"Response dict: {response_data}")
                else:
                    # Try to convert to string
                    response_str = str(response)
                    logger.info(f"Response string: {response_str}")
                    response_data = json.loads(response_str)

            except Exception as api_error:
                logger.error(f"MPESA API Error: {str(api_error)}")
                messages.error(request, f"MPESA API Error: {str(api_error)}")
                return redirect('mpesa:index')

            # Check if we got valid response data
            if not response_data:
                messages.error(request, "No response from MPESA API")
                return redirect('mpesa:index')

            # Log the parsed response
            logger.info(f"Parsed response: {response_data}")

            # Check response code - could be 'ResponseCode' or 'response_code'
            response_code = response_data.get('ResponseCode') or response_data.get(
                'response_code') or response_data.get('errorCode')

            if response_code == '0' or response_code == 0:
                # Success - get checkout ID
                checkout_request_id = response_data.get('CheckoutRequestID') or response_data.get('checkout_request_id')
                merchant_request_id = response_data.get('MerchantRequestID') or response_data.get('merchant_request_id')

                if not checkout_request_id:
                    messages.error(request, "No CheckoutRequestID in response")
                    return redirect('mpesa:index')

                # Store in session
                request.session['last_payment'] = {
                    'phone_number': formatted_phone,
                    'amount': amount_int,
                    'account_reference': account_reference,
                    'checkout_request_id': checkout_request_id,
                    'merchant_request_id': merchant_request_id,
                    'timestamp': datetime.now().isoformat()
                }

                logger.info(f"STK Push successful. CheckoutRequestID: {checkout_request_id}")

                messages.success(request,
                                 f"Payment of KES {amount_int} initiated successfully! "
                                 f"Please check your phone ({phone_number}) to enter your M-Pesa PIN."
                                 )
                return redirect('mpesa:payment_status', checkout_request_id=checkout_request_id)
            else:
                # Failed - get error message
                error_message = response_data.get('ResponseDescription') or response_data.get(
                    'response_description') or response_data.get('errorMessage') or 'Unknown error'
                logger.error(f"STK Push failed: {error_message}")
                messages.error(request, f"Failed to initiate payment: {error_message}")
                return redirect('mpesa:index')

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            messages.error(request, "Invalid response from M-Pesa. Please try again.")
        except Exception as e:
            logger.error(f"Payment initiation error: {str(e)}")
            messages.error(request, f"An error occurred: {str(e)}")
        return redirect('mpesa:index')

    # If not POST, show the payment form
    return render(request, 'mpesa/stk_form.html')
def payment_status(request, checkout_request_id):
    """
    Display payment status page
    """
    context = {
        'checkout_request_id': checkout_request_id,
        'last_payment': request.session.get('last_payment', {})
    }
    return render(request, 'mpesa/payment_status.html', context)


def check_status(request, checkout_request_id):
    """
    AJAX endpoint to check transaction status
    """
    try:
        response = cl.query_stk_status(checkout_request_id)
        response_data = json.loads(response)

        # Log the query response
        logger.info(f"Status query for {checkout_request_id}: {response_data}")

        return JsonResponse(response_data)
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'ResultCode': '1',
            'ResultDesc': 'Failed to check status'
        }, status=500)


@csrf_exempt
def stk_push_callback(request):
    """
    Handle M-Pesa STK Push callback
    """
    if request.method == 'POST':
        try:
            # Parse the callback data
            data = json.loads(request.body.decode('utf-8'))

            # Log the full callback data for debugging
            logger.info("M-Pesa Callback Received:")
            logger.info(json.dumps(data, indent=2))

            # Extract callback metadata
            stk_callback = data.get('Body', {}).get('stkCallback', {})
            result_code = stk_callback.get('ResultCode')
            result_desc = stk_callback.get('ResultDesc')
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            merchant_request_id = stk_callback.get('MerchantRequestID')

            # Initialize response data
            response_data = {
                'checkout_request_id': checkout_request_id,
                'merchant_request_id': merchant_request_id,
                'result_code': result_code,
                'result_desc': result_desc,
                'timestamp': datetime.now().isoformat()
            }

            if result_code == 0:
                # Payment successful
                logger.info(f"Payment successful for CheckoutRequestID: {checkout_request_id}")

                # Extract transaction details from callback metadata
                callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
                metadata = {}

                for item in callback_metadata:
                    name = item.get('Name')
                    value = item.get('Value')
                    metadata[name] = value

                    if name == 'Amount':
                        response_data['amount'] = value
                    elif name == 'MpesaReceiptNumber':
                        response_data['mpesa_receipt'] = value
                    elif name == 'PhoneNumber':
                        response_data['phone_number'] = value
                    elif name == 'TransactionDate':
                        response_data['transaction_date'] = value

                # Here you would typically:
                # 1. Update your database with successful payment
                # 2. Send confirmation email/SMS
                # 3. Update order status, etc.

                logger.info(f"Transaction details: {json.dumps(metadata, indent=2)}")

                # You could also trigger a webhook or notification here
                # send_payment_confirmation(response_data)

            else:
                # Payment failed
                logger.warning(f"Payment failed for CheckoutRequestID: {checkout_request_id}. Reason: {result_desc}")

                # Here you would typically:
                # 1. Update payment status to failed in your database
                # 2. Notify the user
                # 3. Log the failure for analytics

            # Always return success response to M-Pesa
            response = {
                'ResultCode': 0,
                'ResultDesc': 'Success'
            }

            return JsonResponse(response)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in callback: {str(e)}")
            logger.error(f"Raw request body: {request.body}")
            return JsonResponse({
                'ResultCode': 1,
                'ResultDesc': 'Invalid JSON'
            }, status=400)
        except Exception as e:
            logger.error(f"Callback processing error: {str(e)}")
            return JsonResponse({
                'ResultCode': 1,
                'ResultDesc': 'Internal server error'
            }, status=500)

    return JsonResponse({
        'ResultCode': 1,
        'ResultDesc': 'Invalid request method'
    }, status=405)


def format_phone_number(phone):
    """
    Format phone number to 254XXXXXXXXX format
    """
    # Remove any non-digit characters
    phone = ''.join(filter(str.isdigit, phone))

    if len(phone) == 9 and phone.startswith('7'):
        # Format: 712345678 -> 254712345678
        return '254' + phone
    elif len(phone) == 10 and phone.startswith('07'):
        # Format: 0712345678 -> 254712345678
        return '254' + phone[1:]
    elif len(phone) == 12 and phone.startswith('254'):
        # Format: 254712345678
        return phone
    elif len(phone) == 13 and phone.startswith('+254'):
        # Format: +254712345678 -> 254712345678
        return phone[1:]
    else:
        return None


def payment_history(request):
    """
    Display payment history (from session)
    """
    # In a real application, you would query from database
    # For now, we'll use session data
    last_payment = request.session.get('last_payment', {})

    context = {
        'payments': [last_payment] if last_payment else []
    }
    return render(request, 'mpesa/payment_history.html', context)


def test_payment(request):
    """
    Test payment endpoint with your phone number
    """
    try:
        # Your test parameters
        phone_number = '0712759133'  # Your phone number
        amount = 1
        account_reference = 'TEST_PAYMENT'
        transaction_desc = 'Test Payment'

        # Format phone number
        formatted_phone = format_phone_number(phone_number)
        if not formatted_phone:
            return HttpResponse("Invalid phone number format")

        # Get callback URL
        callback_url = request.build_absolute_uri('/mpesa/callback/')

        # Log the test
        logger.info(f"Test payment to {formatted_phone} for KES {amount}")

        # Initiate STK Push
        response = cl.stk_push(
            phone_number=formatted_phone,
            amount=amount,
            account_reference=account_reference,
            transaction_desc=transaction_desc,
            callback_url=callback_url
        )

        # Parse and return response
        response_data = json.loads(response)

        if response_data.get('ResponseCode') == '0':
            # Store in session
            request.session['last_payment'] = {
                'phone_number': formatted_phone,
                'amount': amount,
                'account_reference': account_reference,
                'checkout_request_id': response_data.get('CheckoutRequestID'),
                'merchant_request_id': response_data.get('MerchantRequestID'),
                'timestamp': datetime.now().isoformat(),
                'is_test': True
            }

            # FIXED: Use namespace for redirect
            messages.success(request, f"Test payment initiated! Check your phone ({phone_number})")
            return redirect('mpesa:index')
        else:
            messages.error(request, f"Test payment failed: {response_data.get('ResponseDescription')}")
            return redirect('mpesa:index')

    except Exception as e:
        logger.error(f"Test payment error: {str(e)}")
        messages.error(request, f"Test payment error: {str(e)}")
        return redirect('mpesa:index')


def simulate_payment_page(request):
    """
    Page to simulate/test payments
    """
    return render(request, 'mpesa/test_payment.html')


# Additional utility functions
def get_balance(request):
    """
    Get M-Pesa balance (requires additional permissions)
    """
    try:
        response = cl.account_balance()
        return JsonResponse(json.loads(response))
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def transaction_status(request, transaction_id):
    """
    Check status of a specific transaction
    """
    try:
        response = cl.transaction_status(transaction_id)
        return JsonResponse(json.loads(response))
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)