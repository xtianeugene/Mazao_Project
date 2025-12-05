# payments/views.py
import json
import time
import uuid
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.conf import settings
from decimal import Decimal
from django.views.decorators.http import require_POST, require_GET
from django.urls import reverse
from cart.models import Cart
from .mpesa import MpesaAPI, get_mpesa_api
# Your existing imports
from .models import Payment, Transaction, PaymentConfig

# Setup logger
logger = logging.getLogger(__name__)


def get_mpesa_api():
    """Get MpesaAPI instance with error handling"""
    try:
        # Import the get_mpesa_api function from mpesa module
        from .mpesa import get_mpesa_api as mpesa_getter
        return mpesa_getter()
    except Exception as e:
        logger.error(f"Failed to get MpesaAPI instance: {str(e)}")
        raise ValueError(f"M-Pesa API initialization failed: {str(e)}")

@login_required
def initiate_mpesa_payment(request):
    """Initiate M-Pesa payment from cart"""
    if request.method == 'POST':
        # Get data from POST request
        phone = request.POST.get('phone')
        amount = request.POST.get('amount')
        delivery_address = request.POST.get('delivery_address', '')
        delivery_instructions = request.POST.get('delivery_instructions', '')
        delivery_method = request.POST.get('delivery_method', 'pickup')

        # Validate phone number
        if phone:
            # Clean phone number
            phone = phone.strip()
            if phone.startswith('0'):
                phone = '254' + phone[1:]  # Convert 07... to 2547...
            elif phone.startswith('+254'):
                phone = phone[1:]  # Remove + from +254...
            elif phone.startswith('254'):
                pass  # Already correct format
            else:
                messages.error(request, "Invalid phone number format. Use: 07..., 254..., or +254...")
                return redirect('cart:checkout')

        # Validate amount
        try:
            amount_decimal = Decimal(amount)
            if amount_decimal < 1:
                messages.error(request, "Amount must be at least 1 KSH")
                return redirect('cart:checkout')
        except (ValueError, TypeError):
            messages.error(request, "Invalid amount")
            return redirect('cart:checkout')

        # Get cart info
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.all()
            cart_total = sum(item.product.price * item.quantity for item in cart_items)

            # Validate cart total matches amount
            if cart_total != amount_decimal:
                messages.warning(request, f"Cart total ({cart_total}) doesn't match payment amount")
        except Cart.DoesNotExist:
            messages.error(request, "Cart not found")
            return redirect('cart:view_cart')

        # Store in session for later use
        request.session['checkout_data'] = {
            'phone': phone,
            'amount': str(amount_decimal),
            'delivery_address': delivery_address,
            'delivery_instructions': delivery_instructions,
            'delivery_method': delivery_method,
            'cart_id': str(cart.id) if cart else None,
            'cart_total': str(cart_total) if cart else '0',
        }
        request.session.modified = True

        context = {
            'title': 'M-Pesa Payment',
            'amount': amount_decimal,
            'phone': phone,
            'cart': cart,
            'cart_items': cart_items if cart else [],
            'cart_total': cart_total if cart else 0,
            'delivery_address': delivery_address,
            'delivery_instructions': delivery_instructions,
            'delivery_method': delivery_method,
        }

        return render(request, 'payments/initiate_mpesa.html', context)

    # If GET request, check session for data
    elif request.method == 'GET':
        # Try to get from session first
        checkout_data = request.session.get('checkout_data', {})

        # Get from GET parameters as fallback
        amount = request.GET.get('amount') or checkout_data.get('amount')
        phone = request.GET.get('phone') or checkout_data.get('phone')

        if not amount or not phone:
            messages.error(request, "Missing payment information")
            return redirect('cart:checkout')

        # Get cart
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.all()
            cart_total = sum(item.product.price * item.quantity for item in cart_items)
        except Cart.DoesNotExist:
            cart = None
            cart_items = []
            cart_total = 0

        context = {
            'title': 'M-Pesa Payment',
            'amount': amount,
            'phone': phone,
            'cart': cart,
            'cart_items': cart_items,
            'cart_total': cart_total,
        }

        return render(request, 'payments/initiate_mpesa.html', context)

    return redirect('cart:checkout')


@login_required
@require_POST
def process_mpesa_payment(request):
    """Process M-Pesa payment request"""
    try:
        # Get data from POST
        phone = request.POST.get('phone') or request.POST.get('confirm_phone')
        amount = request.POST.get('amount')

        # Validate required fields
        if not phone or not amount:
            messages.error(request, "Phone number and amount are required")
            return redirect('payments:initiate_mpesa')

        # Get checkout data from session
        checkout_data = request.session.get('checkout_data', {})

        # Update with current values if provided
        if phone:
            checkout_data['phone'] = phone
        if amount:
            checkout_data['amount'] = amount

        # Get delivery info
        delivery_address = checkout_data.get('delivery_address', '')
        delivery_instructions = checkout_data.get('delivery_instructions', '')
        delivery_method = checkout_data.get('delivery_method', 'pickup')
        cart_id = checkout_data.get('cart_id')

        # Get cart
        cart = None
        if cart_id:
            try:
                cart = Cart.objects.get(id=cart_id, user=request.user)
            except Cart.DoesNotExist:
                pass

        # Initialize M-Pesa API
        try:
            mpesa_api = get_mpesa_api()
        except Exception as e:
            logger.error(f"M-Pesa API initialization failed: {str(e)}")
            messages.error(request, "Payment service is temporarily unavailable. Please try again later.")
            return redirect('payments:initiate_mpesa')

        # Create payment record
        try:
            payment = Payment.objects.create(
                user=request.user,
                amount=Decimal(amount),
                phone_number=phone,
                description="Cart payment",
                status='pending',
                payment_method='mpesa',
                delivery_address=delivery_address,
                delivery_instructions=delivery_instructions,
                delivery_method=delivery_method,
                cart_id=cart_id,
            )
        except Exception as e:
            logger.error(f"Failed to create payment record: {str(e)}")
            messages.error(request, "Failed to create payment record. Please try again.")
            return redirect('payments:initiate_mpesa')

        # Generate callback URL
        try:
            callback_url = request.build_absolute_uri(reverse('payments:mpesa_callback'))
        except:
            # Fallback to direct URL
            callback_url = request.build_absolute_uri('/payments/mpesa-callback/')

        # Initiate STK Push
        try:
            result = mpesa_api.stk_push(
                phone_number=phone,
                amount=Decimal(amount),
                account_reference=f"CART-{payment.id.hex[:8].upper()}",
                transaction_desc="Cart payment",
                callback_url=callback_url
            )

            logger.info(f"STK Push result: {json.dumps(result, indent=2)}")

            if result.get('success'):
                # Update payment with M-Pesa details
                payment.merchant_request_id = result.get('merchant_request_id')
                payment.checkout_request_id = result.get('checkout_request_id')
                payment.status = 'initiated'
                payment.raw_response = result
                payment.save()

                # Store payment ID in session
                request.session['mpesa_payment_id'] = str(payment.id)
                request.session['mpesa_checkout_id'] = result.get('checkout_request_id')
                request.session.modified = True

                # Clear checkout data from session
                if 'checkout_data' in request.session:
                    del request.session['checkout_data']

                # Redirect to processing page
                return redirect('payments:mpesa_processing', payment_id=payment.id)

            else:
                # Payment initiation failed
                payment.status = 'failed'
                payment.result_description = result.get('error_message', 'Payment initiation failed')
                payment.raw_response = result
                payment.save()

                error_msg = result.get('error_message', 'Failed to initiate payment. Please try again.')
                logger.error(f"STK Push failed: {error_msg}")
                messages.error(request, f"Payment failed: {error_msg}")
                return redirect('payments:initiate_mpesa')

        except Exception as e:
            logger.error(f"STK Push exception: {str(e)}")
            payment.status = 'failed'
            payment.result_description = str(e)
            payment.save()

            messages.error(request, f"Error initiating payment: {str(e)}")
            return redirect('payments:initiate_mpesa')

    except Exception as e:
        logger.error(f"Process payment exception: {str(e)}", exc_info=True)
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return redirect('payments:initiate_mpesa')


@login_required
def mpesa_payment_processing(request, payment_id):
    """Show M-Pesa payment processing page"""
    try:
        payment = get_object_or_404(Payment, id=payment_id, user=request.user)

        # Check if payment is already completed
        if payment.is_complete:
            if payment.status == 'success':
                return redirect('payments:payment_success')
            elif payment.status == 'failed':
                messages.error(request, f"Payment failed: {payment.result_description}")
                return redirect('payments:initiate_mpesa')

        # Get cart info for display
        cart = None
        cart_items = []
        if payment.cart_id:
            try:
                cart = Cart.objects.get(id=payment.cart_id, user=request.user)
                cart_items = cart.items.all()
            except Cart.DoesNotExist:
                pass

        context = {
            'title': 'M-Pesa Payment Processing',
            'payment': payment,
            'payment_id': payment.id,
            'amount': payment.amount,
            'phone': payment.phone_number,
            'cart': cart,
            'cart_items': cart_items,
            'checkout_request_id': payment.checkout_request_id,
            'polling_interval': 5000,  # 5 seconds for AJAX polling
        }

        return render(request, 'payments/mpesa_processing.html', context)

    except Exception as e:
        logger.error(f"Error loading processing page: {str(e)}")
        messages.error(request, "Payment not found")
        return redirect('payments:initiate_mpesa')


@login_required
def check_payment_status(request, payment_id):
    """Check payment status via AJAX"""
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    try:
        payment = get_object_or_404(Payment, id=payment_id, user=request.user)

        # If payment is already complete, return status
        if payment.is_complete:
            return JsonResponse({
                'status': payment.status,
                'is_complete': True,
                'receipt_number': payment.mpesa_receipt_number,
                'result_description': payment.result_description,
                'message': 'Payment already processed'
            })

        # If payment is initiated but not complete, query M-Pesa API
        if payment.status == 'initiated' and payment.checkout_request_id:
            try:
                mpesa_api = get_mpesa_api()
                result = mpesa_api.query_status(payment.checkout_request_id)

                logger.info(f"Query status result: {json.dumps(result, indent=2)}")

                if result.get('success'):
                    result_code = result.get('result_code', '')

                    # Check result code
                    if result_code == '0':
                        # Payment successful
                        receipt_number = result.get('mpesa_receipt_number', '')

                        payment.mark_as_successful(
                            receipt_number=receipt_number,
                            result_code=result_code,
                            result_description=result.get('result_description', 'Success')
                        )

                        # Handle successful payment (create order, etc.)
                        handle_successful_payment(request, payment)

                        return JsonResponse({
                            'status': 'success',
                            'is_complete': True,
                            'receipt_number': receipt_number,
                            'result_description': result.get('result_description'),
                            'message': 'Payment successful!',
                            'redirect_url': reverse('payments:payment_success')
                        })

                    elif result_code in ['1032', '1037', '1031']:  # Timeout or cancelled
                        payment.mark_as_failed(
                            result_code=result_code,
                            result_description=result.get('result_description', 'Payment cancelled or timed out')
                        )

                        return JsonResponse({
                            'status': 'cancelled',
                            'is_complete': True,
                            'result_description': result.get('result_description'),
                            'message': 'Payment was cancelled or timed out.'
                        })

                    else:
                        # Other error codes
                        payment.mark_as_failed(
                            result_code=result_code,
                            result_description=result.get('result_description', 'Payment failed')
                        )

                        return JsonResponse({
                            'status': 'failed',
                            'is_complete': True,
                            'result_description': result.get('result_description'),
                            'message': result.get('result_description', 'Payment failed')
                        })

                else:
                    # Query failed
                    error_msg = result.get('error_message', 'Failed to query payment status')
                    logger.error(f"Query status failed: {error_msg}")

                    return JsonResponse({
                        'status': 'error',
                        'is_complete': False,
                        'message': error_msg
                    })

            except Exception as e:
                logger.error(f"Query status exception: {str(e)}")
                return JsonResponse({
                    'status': 'error',
                    'is_complete': False,
                    'message': f'Error checking status: {str(e)}'
                })

        # Return current status if no query was made
        return JsonResponse({
            'status': payment.status,
            'is_complete': payment.is_complete,
            'receipt_number': payment.mpesa_receipt_number,
            'result_description': payment.result_description,
            'message': payment.result_description or 'Waiting for payment confirmation...'
        })

    except Exception as e:
        logger.error(f"Check status exception: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_POST
def mpesa_callback(request):
    """Handle M-Pesa callback (called by Safaricom)"""
    try:
        # Parse request body
        body = request.body.decode('utf-8')
        data = json.loads(body) if body else {}

        logger.info(f"M-Pesa Callback received: {json.dumps(data, indent=2)}")

        # Extract callback data
        stk_callback = data.get('Body', {}).get('stkCallback', {})
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')

        if not checkout_request_id:
            logger.warning("No CheckoutRequestID in callback")
            return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid request'})

        # Find payment by checkout request ID
        try:
            payment = Payment.objects.get(checkout_request_id=checkout_request_id)
            logger.info(f"Found payment: {payment.id} for checkout: {checkout_request_id}")
        except Payment.DoesNotExist:
            logger.warning(f"Payment not found for checkout: {checkout_request_id}")
            return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Payment not found'})

        # Process based on result code
        if result_code == 0:
            # Payment successful
            callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])

            receipt_number = None
            amount = None
            phone_number = None
            transaction_date = None

            # Extract metadata
            for item in callback_metadata:
                name = item.get('Name')
                value = item.get('Value')

                if name == 'MpesaReceiptNumber':
                    receipt_number = value
                elif name == 'Amount':
                    amount = value
                elif name == 'PhoneNumber':
                    phone_number = value
                elif name == 'TransactionDate':
                    transaction_date = value

            if receipt_number:
                payment.mark_as_successful(
                    receipt_number=receipt_number,
                    result_code=str(result_code),
                    result_description=result_desc
                )

                # Update additional fields if available
                if amount:
                    try:
                        payment.mpesa_amount = Decimal(amount)
                    except:
                        pass
                if phone_number:
                    payment.mpesa_phone = phone_number
                if transaction_date:
                    payment.transaction_date = transaction_date

                payment.save()

                # Handle successful payment (async or sync)
                handle_successful_payment_from_callback(payment)

                logger.info(f"Payment {payment.id} marked as successful. Receipt: {receipt_number}")
            else:
                logger.warning(f"Successful payment but no receipt number: {checkout_request_id}")
                payment.mark_as_successful(
                    receipt_number='PENDING',
                    result_code=str(result_code),
                    result_description=result_desc
                )
                payment.save()

        else:
            # Payment failed
            payment.mark_as_failed(
                result_code=str(result_code),
                result_description=result_desc
            )
            payment.save()
            logger.info(f"Payment {payment.id} marked as failed. Code: {result_code}, Desc: {result_desc}")

        # Always return success to M-Pesa
        return JsonResponse({
            'ResultCode': 0,
            'ResultDesc': 'Success'
        })

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in callback: {str(e)}")
        return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid JSON'})
    except Exception as e:
        logger.error(f"Error processing callback: {str(e)}", exc_info=True)
        return JsonResponse({
            'ResultCode': 1,
            'ResultDesc': 'Processing error'
        })


def handle_successful_payment(request, payment):
    """Handle successful payment - create order from cart"""
    try:
        # Get cart ID from payment
        cart_id = payment.cart_id

        if cart_id:
            # Get cart
            cart = Cart.objects.get(id=cart_id, user=payment.user)

            # Create order
            from orders.models import Order, OrderItem

            # Generate order number
            order_number = f"ORD-{payment.id.hex[:8].upper()}-{int(time.time())}"

            order = Order.objects.create(
                user=payment.user,
                order_number=order_number,
                total_amount=payment.amount,
                payment_method='mpesa',
                payment_status='paid',
                payment_reference=payment.mpesa_receipt_number,
                status='processing',
                delivery_address=payment.delivery_address,
                delivery_instructions=payment.delivery_instructions,
                delivery_method=payment.delivery_method,
                phone_number=payment.phone_number
            )

            # Add cart items to order
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price,
                    subtotal=cart_item.product.price * cart_item.quantity
                )

            # Clear cart
            cart.items.all().delete()

            # Link order to payment
            payment.order = order
            payment.order_created = True
            payment.save()

            # Store order ID in session for success page
            request.session['last_order_id'] = order.id
            request.session['last_payment_id'] = str(payment.id)
            request.session.modified = True

            logger.info(f"Created order {order.id} for payment {payment.id}")

            return True
        else:
            logger.warning(f"No cart ID for payment {payment.id}")
            return False

    except Exception as e:
        logger.error(f"Error creating order for payment {payment.id}: {str(e)}", exc_info=True)

        # Mark payment for manual review
        payment.order_created = False
        payment.result_description = f"Payment successful but order creation failed: {str(e)}"
        payment.save()

        return False


def handle_successful_payment_from_callback(payment):
    """Handle successful payment from callback"""
    try:
        # Try to create order if not already created
        if not payment.order_created and payment.cart_id:
            # Import here to avoid circular imports
            from django.contrib.auth.models import User
            from cart.models import Cart
            from orders.models import Order, OrderItem

            # Get user and cart
            user = payment.user
            cart = Cart.objects.get(id=payment.cart_id, user=user)

            # Create order
            order_number = f"ORD-CB-{payment.id.hex[:8].upper()}-{int(time.time())}"

            order = Order.objects.create(
                user=user,
                order_number=order_number,
                total_amount=payment.amount,
                payment_method='mpesa',
                payment_status='paid',
                payment_reference=payment.mpesa_receipt_number,
                status='processing',
                delivery_address=payment.delivery_address,
                delivery_instructions=payment.delivery_instructions,
                delivery_method=payment.delivery_method,
                phone_number=payment.phone_number
            )

            # Add cart items to order
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price,
                    subtotal=cart_item.product.price * cart_item.quantity
                )

            # Clear cart
            cart.items.all().delete()

            # Link order to payment
            payment.order = order
            payment.order_created = True
            payment.save()

            logger.info(f"Created order {order.id} from callback for payment {payment.id}")

        return True

    except Exception as e:
        logger.error(f"Error creating order from callback for payment {payment.id}: {str(e)}")
        return False


@login_required
def payment_success(request):
    """Payment success page"""
    order_id = request.session.get('last_order_id')
    payment_id = request.session.get('last_payment_id')

    order = None
    payment = None

    if order_id:
        try:
            from orders.models import Order
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            pass

    if payment_id:
        try:
            payment = Payment.objects.get(id=payment_id, user=request.user)
        except Payment.DoesNotExist:
            pass

    # Clear session data
    if 'last_order_id' in request.session:
        del request.session['last_order_id']
    if 'last_payment_id' in request.session:
        del request.session['last_payment_id']
    request.session.modified = True

    context = {
        'title': 'Payment Successful',
        'order': order,
        'payment': payment,
    }

    return render(request, 'payments/payment_success.html', context)


@login_required
def payment_failed(request, payment_id=None):
    """Payment failed page"""
    payment = None
    if payment_id:
        try:
            payment = Payment.objects.get(id=payment_id, user=request.user)
        except Payment.DoesNotExist:
            pass

    context = {
        'title': 'Payment Failed',
        'payment': payment,
    }

    return render(request, 'payments/payment_failed.html', context)


@login_required
def payment_history(request):
    """View payment history"""
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'title': 'Payment History',
        'payments': payments,
    }

    return render(request, 'payments/payment_history.html', context)


@login_required
def payment_detail(request, payment_id):
    """View payment details"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)

    context = {
        'title': 'Payment Details',
        'payment': payment,
    }

    return render(request, 'payments/payment_detail.html', context)


@login_required
@require_POST
def cancel_payment(request, payment_id):
    """Cancel a pending payment"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)

    if payment.status in ['pending', 'initiated']:
        payment.status = 'cancelled'
        payment.result_description = 'Cancelled by user'
        payment.save()

        messages.success(request, "Payment cancelled successfully")
    else:
        messages.error(request, "Cannot cancel payment in current status")

    return redirect('payments:payment_history')


@login_required
def retry_payment(request, payment_id):
    """Retry a failed payment"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)

    if payment.status == 'failed':
        # Store payment info in session for retry
        request.session['checkout_data'] = {
            'phone': payment.phone_number,
            'amount': str(payment.amount),
            'delivery_address': payment.delivery_address,
            'delivery_instructions': payment.delivery_instructions,
            'delivery_method': payment.delivery_method,
            'cart_id': payment.cart_id,
        }
        request.session.modified = True

        return redirect('payments:initiate_mpesa')
    else:
        messages.error(request, "Cannot retry payment in current status")
        return redirect('payments:payment_history')