# cart/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import transaction
from decimal import Decimal
import json
import uuid

# Import models
from products.models import Product
from orders.models import Order, OrderItem
from payments.models import MpesaTransaction
from .models import Cart, CartItem
from .forms import CartItemForm, CheckoutForm

# Import M-Pesa functions from your payments app
try:
    from payments.mpesa import (
        get_access_token,
        stk_push,
        query_stk_status,
        generate_timestamp,
        generate_password,
        format_phone_number
    )

    MPESA_AVAILABLE = True
except ImportError:
    MPESA_AVAILABLE = False
    print("Warning: M-Pesa module not available. Install payments app and configure M-Pesa.")


# cart/views.py
@login_required
def add_to_cart(request, product_id):
    """Simple add to cart - no JavaScript needed"""
    if request.method == 'POST':
        return _add_to_cart_logic(request, product_id, redirect_to_cart=False)
    return redirect('products:product_detail', slug=product.slug)


@login_required
def buy_now(request, product_id):
    """Add to cart and go directly to checkout"""
    if request.method == 'POST':
        return _add_to_cart_logic(request, product_id, redirect_to_cart=True)
    return redirect('products:product_detail', slug=product.slug)


def _add_to_cart_logic(request, product_id, redirect_to_cart=False):
    """Shared logic for both actions"""
    product = get_object_or_404(Product, id=product_id)

    # Check if user is trying to buy their own product
    if request.user == product.seller:
        messages.error(request, "You cannot purchase your own products.")
        return redirect('products:product_detail', slug=product.slug)

    # Check if product is available
    if not product.is_available:
        messages.error(request, f"'{product.name}' is not available.")
        return redirect('products:product_detail', slug=product.slug)

    # Get quantity
    try:
        quantity = Decimal(str(request.POST.get('quantity', 1)))
    except:
        quantity = Decimal('1')

    # Validate quantity
    if quantity > Decimal(str(product.quantity)):
        messages.error(request, f"Only {product.quantity} {product.get_unit_display()} available.")
        return redirect('products:product_detail', slug=product.slug)

    if quantity < product.min_order_quantity:
        messages.error(request, f"Minimum order quantity is {product.min_order_quantity} {product.get_unit_display()}.")
        return redirect('products:product_detail', slug=product.slug)

    # Get or create user's cart
    cart, created = Cart.objects.get_or_create(user=request.user)

    # Check if product already exists in cart
    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )

    if not item_created:
        cart_item.quantity += quantity
        cart_item.save()

    # Show success message
    messages.success(request, f"Added {quantity} {product.get_unit_display()} of '{product.name}' to cart.")

    # Redirect based on action
    if redirect_to_cart:
        return redirect('cart:view_cart')
    else:
        return redirect('products:product_detail', slug=product.slug)
@login_required
def remove_from_cart(request, item_id):
    """Remove an item from the cart"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.success(request, f"Removed '{product_name}' from cart.")
    return redirect('cart:view_cart')


@login_required
def update_cart_item(request, item_id):
    """Update quantity of a cart item"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product = cart_item.product

    if request.method == 'POST':
        quantity = request.POST.get('quantity')
        try:
            quantity = Decimal(quantity)

            # Validate against product availability
            if quantity > Decimal(str(product.quantity)):
                messages.error(request, f"Only {product.quantity} {product.get_unit_display()} available.")
                return redirect('cart:view_cart')

            if quantity <= 0:
                cart_item.delete()
                messages.success(request, "Item removed from cart.")
            else:
                cart_item.quantity = quantity
                cart_item.save()
                messages.success(request, "Cart updated successfully.")
        except (ValueError, TypeError):
            messages.error(request, "Invalid quantity.")

    return redirect('cart:view_cart')


@login_required
def view_cart(request):
    """View the shopping cart"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all().select_related('product')

    # Calculate totals
    subtotal = sum(item.total_price for item in cart_items)
    delivery_fee = calculate_delivery_fee(cart_items)
    total = subtotal + delivery_fee

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'total': total,
    }
    return render(request, 'cart/cart.html', context)


def calculate_delivery_fee(cart_items):
    """Calculate delivery fee based on items"""
    # Simple logic: KES 200 if any item requires delivery
    for item in cart_items:
        if item.delivery_method == 'delivery':
            return Decimal('200.00')
    return Decimal('0.00')


@login_required
def cart_item_count(request):
    """Get cart item count for AJAX requests"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        count = cart.items.count()
    else:
        count = 0

    return JsonResponse({'count': count})


@login_required
def checkout(request):
    """Checkout page"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart).select_related('product')

        if not cart_items.exists():
            messages.warning(request, "Your cart is empty!")
            return redirect('cart:view_cart')

        # Validate all items are available
        unavailable_items = []
        for item in cart_items:
            if not item.product.is_available:
                unavailable_items.append(item.product.name)
            elif Decimal(str(item.quantity)) > Decimal(str(item.product.quantity)):
                unavailable_items.append(f"{item.product.name} (only {item.product.quantity} available)")

        if unavailable_items:
            messages.error(request, f"Some items are unavailable: {', '.join(unavailable_items)}")
            return redirect('cart:view_cart')

    except Cart.DoesNotExist:
        messages.warning(request, "Your cart is empty!")
        return redirect('cart:view_cart')

    # Calculate totals
    subtotal = sum(item.total_price for item in cart_items)
    delivery_fee = calculate_delivery_fee(cart_items)
    total = subtotal + delivery_fee

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Save checkout data to session
            request.session['checkout_data'] = {
                'delivery_address': form.cleaned_data['delivery_address'],
                'delivery_instructions': form.cleaned_data['delivery_instructions'],
                'payment_method': form.cleaned_data['payment_method'],
                'phone_number': form.cleaned_data.get('phone_number', ''),
            }

            payment_method = form.cleaned_data['payment_method']

            if payment_method == 'mpesa':
                return redirect('cart:mpesa_payment')
            elif payment_method == 'cash':
                return redirect('cart:cash_on_delivery')
            elif payment_method == 'bank':
                return redirect('cart:bank_transfer')
    else:
        # Pre-fill form with user data
        initial_data = {}
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            initial_data = {
                'delivery_address': profile.address or '',
                'phone_number': profile.phone_number or '',
            }
        form = CheckoutForm(initial=initial_data)

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'total': total,
        'form': form,
        'mpesa_available': MPESA_AVAILABLE,
    }
    return render(request, 'cart/checkout.html', context)


@login_required
def mpesa_payment(request):
    """Handle M-Pesa payment"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)

        if not cart_items.exists():
            messages.warning(request, "Your cart is empty!")
            return redirect('cart:view_cart')

        # Get checkout data from session
        checkout_data = request.session.get('checkout_data', {})
        if not checkout_data:
            messages.error(request, "Please complete checkout first.")
            return redirect('cart:checkout')

        # Calculate total
        subtotal = sum(item.total_price for item in cart_items)
        delivery_fee = calculate_delivery_fee(cart_items)
        total_amount = subtotal + delivery_fee

        phone_number = checkout_data.get('phone_number', '')

        if request.method == 'POST':
            if not MPESA_AVAILABLE:
                messages.error(request, "M-Pesa payment is currently unavailable.")
                return redirect('cart:checkout')

            # Format phone number
            phone_number = format_phone_number(phone_number)
            if not phone_number:
                messages.error(request, "Invalid phone number format.")
                return render(request, 'cart/mpesa_payment.html', {
                    'total': total_amount,
                    'phone_number': phone_number,
                    'cart': cart
                })

            try:
                # Get access token
                access_token = get_access_token()
                if not access_token:
                    messages.error(request, "Failed to initialize payment. Please try again.")
                    return redirect('cart:checkout')

                # Generate unique transaction reference
                transaction_ref = f"MZ{str(uuid.uuid4().int)[:8]}"

                # Initiate STK push
                response = stk_push(
                    access_token=access_token,
                    phone_number=phone_number,
                    amount=float(total_amount),  # Convert to float for M-Pesa API
                    account_reference=transaction_ref,
                    transaction_desc=f"Payment for order {transaction_ref}"
                )

                if response.get('ResponseCode') == '0':
                    # Create M-Pesa transaction record
                    transaction = MpesaTransaction.objects.create(
                        user=request.user,
                        phone_number=phone_number,
                        amount=total_amount,
                        transaction_ref=transaction_ref,
                        checkout_request_id=response.get('CheckoutRequestID'),
                        merchant_request_id=response.get('MerchantRequestID'),
                        status='PENDING'
                    )

                    # Store transaction ID in session
                    request.session['mpesa_transaction_id'] = transaction.id

                    messages.success(request, "M-Pesa payment initiated. Please check your phone to complete.")
                    return redirect('cart:payment_status', transaction_id=transaction.id)
                else:
                    messages.error(request,
                                   f"Failed to initiate payment: {response.get('ResponseDescription', 'Unknown error')}")

            except Exception as e:
                messages.error(request, f"Payment error: {str(e)}")
                return redirect('cart:checkout')

        context = {
            'total': total_amount,
            'phone_number': phone_number,
            'cart': cart,
            'cart_items': cart_items,
            'mpesa_available': MPESA_AVAILABLE,
        }
        return render(request, 'cart/mpesa_payment.html', context)

    except Cart.DoesNotExist:
        messages.warning(request, "Your cart is empty!")
        return redirect('cart:view_cart')


@login_required
def payment_status(request, transaction_id):
    """Check M-Pesa payment status"""
    try:
        transaction = MpesaTransaction.objects.get(id=transaction_id, user=request.user)

        if transaction.status == 'SUCCESS':
            # Payment successful, create order
            return create_order_from_cart(request, transaction)
        elif transaction.status == 'PENDING':
            # Check status
            if MPESA_AVAILABLE:
                try:
                    access_token = get_access_token()
                    status_response = query_stk_status(
                        access_token=access_token,
                        checkout_request_id=transaction.checkout_request_id
                    )

                    if status_response.get('ResultCode') == '0':
                        transaction.status = 'SUCCESS'
                        transaction.result_code = status_response.get('ResultCode')
                        transaction.result_desc = status_response.get('ResultDesc')
                        transaction.save()

                        # Create order
                        return create_order_from_cart(request, transaction)
                    else:
                        transaction.status = 'FAILED'
                        transaction.result_code = status_response.get('ResultCode')
                        transaction.result_desc = status_response.get('ResultDesc')
                        transaction.save()

                        messages.error(request, f"Payment failed: {status_response.get('ResultDesc')}")
                        return redirect('cart:checkout')
                except Exception as e:
                    messages.error(request, f"Error checking payment status: {str(e)}")

        context = {
            'transaction': transaction,
            'mpesa_available': MPESA_AVAILABLE,
        }
        return render(request, 'cart/payment_status.html', context)

    except MpesaTransaction.DoesNotExist:
        messages.error(request, "Transaction not found.")
        return redirect('cart:checkout')


@login_required
@transaction.atomic
def create_order_from_cart(request, mpesa_transaction=None):
    """Create order from cart items after successful payment"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)
        checkout_data = request.session.get('checkout_data', {})

        if not cart_items.exists():
            messages.warning(request, "Your cart is empty!")
            return redirect('cart:view_cart')

        # Calculate totals
        subtotal = sum(item.total_price for item in cart_items)
        delivery_fee = calculate_delivery_fee(cart_items)
        total_amount = subtotal + delivery_fee

        # Determine delivery method (if any item requires delivery, use delivery)
        delivery_method = 'pickup'
        for item in cart_items:
            if item.delivery_method == 'delivery':
                delivery_method = 'delivery'
                break

        # Determine payment method
        payment_method = checkout_data.get('payment_method', 'cash')
        payment_status = 'paid' if mpesa_transaction else 'pending'

        # Create order
        order = Order.objects.create(
            user=request.user,
            delivery_address=checkout_data.get('delivery_address', ''),
            delivery_instructions=checkout_data.get('delivery_instructions', ''),
            delivery_method=delivery_method,
            payment_method=payment_method,
            payment_status=payment_status,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total_amount=total_amount,
            order_status='pending'
        )

        # Link M-Pesa transaction if exists
        if mpesa_transaction:
            mpesa_transaction.order = order
            mpesa_transaction.save()

        # Create order items
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                unit_price=cart_item.product.price,
                delivery_method=cart_item.delivery_method,
                special_instructions=cart_item.special_instructions
            )

            # Update product quantity
            product = cart_item.product
            product.quantity -= Decimal(str(cart_item.quantity))
            if product.quantity <= 0:
                product.status = Product.ProductStatus.OUT_OF_STOCK
            product.save()

        # Clear cart
        cart.items.all().delete()

        # Clear session data
        if 'checkout_data' in request.session:
            del request.session['checkout_data']
        if 'mpesa_transaction_id' in request.session:
            del request.session['mpesa_transaction_id']

        messages.success(request, f"Order #{order.order_number} placed successfully!")
        return redirect('cart:order_confirmation', order_id=order.id)

    except Exception as e:
        messages.error(request, f"Error creating order: {str(e)}")
        return redirect('cart:checkout')


@login_required
def cash_on_delivery(request):
    """Handle cash on delivery"""
    try:
        checkout_data = request.session.get('checkout_data', {})
        if not checkout_data:
            messages.error(request, "Please complete checkout first.")
            return redirect('cart:checkout')

        # Create order
        order = create_order_from_cart(request)

        messages.success(request, f"Order #{order.order_number} placed successfully! You'll pay on delivery.")
        return redirect('cart:order_confirmation', order_id=order.id)

    except Exception as e:
        messages.error(request, f"Error processing order: {str(e)}")
        return redirect('cart:checkout')


@login_required
def bank_transfer(request):
    """Handle bank transfer"""
    try:
        checkout_data = request.session.get('checkout_data', {})
        if not checkout_data:
            messages.error(request, "Please complete checkout first.")
            return redirect('cart:checkout')

        # Store payment method as bank transfer
        checkout_data['payment_method'] = 'bank'
        request.session['checkout_data'] = checkout_data

        # Show bank details page
        return render(request, 'cart/bank_transfer.html', {
            'bank_details': get_bank_details()
        })

    except Exception as e:
        messages.error(request, f"Error processing bank transfer: {str(e)}")
        return redirect('cart:checkout')


def get_bank_details():
    """Get bank transfer details"""
    return {
        'bank_name': 'Equity Bank',
        'account_name': 'Mazao Farmers Market',
        'account_number': '1234567890',
        'branch': 'Nairobi CBD',
        'swift_code': 'EQBLKENA',
    }


@login_required
def order_confirmation(request, order_id):
    """Order confirmation page"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        order_items = order.items.all()

        context = {
            'order': order,
            'order_items': order_items,
        }
        return render(request, 'cart/order_confirmation.html', context)

    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('cart:view_cart')


@csrf_exempt
def mpesa_callback(request):
    """Handle M-Pesa callback (for payment confirmation)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # Extract transaction details
            checkout_request_id = data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID', '')
            result_code = data.get('Body', {}).get('stkCallback', {}).get('ResultCode', '')
            result_desc = data.get('Body', {}).get('stkCallback', {}).get('ResultDesc', '')

            # Find transaction
            try:
                transaction = MpesaTransaction.objects.get(checkout_request_id=checkout_request_id)

                if result_code == '0':
                    transaction.status = 'SUCCESS'
                    transaction.result_code = result_code
                    transaction.result_desc = result_desc

                    # Extract payment details if available
                    callback_metadata = data.get('Body', {}).get('stkCallback', {}).get('CallbackMetadata', {}).get(
                        'Item', [])
                    for item in callback_metadata:
                        if item.get('Name') == 'Amount':
                            transaction.amount = Decimal(str(item.get('Value', transaction.amount)))
                        elif item.get('Name') == 'MpesaReceiptNumber':
                            transaction.mpesa_receipt = item.get('Value', '')
                        elif item.get('Name') == 'PhoneNumber':
                            transaction.phone_number = item.get('Value', transaction.phone_number)

                    transaction.save()

                    # TODO: You could trigger automatic order creation here
                    # But better to let the user complete it via the payment_status view

                else:
                    transaction.status = 'FAILED'
                    transaction.result_code = result_code
                    transaction.result_desc = result_desc
                    transaction.save()

            except MpesaTransaction.DoesNotExist:
                pass  # Transaction not found

            return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})

        except Exception as e:
            print(f"M-Pesa callback error: {e}")
            return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Failed'})

    return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid request method'})


@login_required
def process_payment(request):
    """Process payment from checkout"""
    if request.method == 'POST':
        phone = request.POST.get('phone')
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method', 'mpesa')

        # Get user's cart
        cart = Cart.objects.get(user=request.user)

        # Process payment based on method
        if payment_method == 'mpesa':
            # Call your M-Pesa payment function
            # return initiate_mpesa_payment(request, phone, amount, cart)
            messages.info(request, "M-Pesa payment would be processed here.")
            return redirect('cart:payment_processing')

        elif payment_method == 'cash_on_delivery':
            # Create COD order
            # return create_cod_order(request, cart)
            messages.success(request, "Cash on Delivery order created!")
            return redirect('orders:order_success')

        elif payment_method == 'bank_transfer':
            # Show bank transfer instructions
            messages.info(request, "Bank transfer instructions sent.")
            return render(request, 'cart/bank_transfer.html')

    # If GET request, redirect to checkout
    return redirect('cart:checkout')


@login_required
def payment_processing(request):
    """Show payment processing page"""
    # Get any pending payment info from session
    payment_id = request.session.get('pending_payment_id')

    context = {
        'title': 'Payment Processing',
        'payment_id': payment_id,
    }

    return render(request, 'cart/payment_processing.html', context)


@login_required
def payment_success(request):
    """Payment success page"""
    # Clear any pending payment from session
    if 'pending_payment_id' in request.session:
        del request.session['pending_payment_id']

    messages.success(request, "Payment successful! Thank you for your order.")
    return render(request, 'cart/payment_success.html', {'title': 'Payment Successful'})


@login_required
def payment_failed(request):
    """Payment failed page"""
    error_message = request.GET.get('error', 'Payment failed. Please try again.')
    messages.error(request, error_message)
    return render(request, 'cart/payment_failed.html', {'title': 'Payment Failed'})


@login_required
def cash_on_delivery(request):
    """Handle cash on delivery"""
    if request.method == 'POST':
        # Get cart
        cart = Cart.objects.get(user=request.user)

        # Create COD order
        # ... your order creation logic ...

        messages.success(request, "Order placed successfully! You'll pay on delivery.")
        return redirect('cart:payment_success')

    return redirect('cart:checkout')


@login_required
def bank_transfer(request):
    """Show bank transfer instructions"""
    cart = Cart.objects.get(user=request.user)

    context = {
        'cart': cart,
        'total_amount': cart.get_total(),
        'title': 'Bank Transfer Instructions'
    }

    return render(request, 'cart/bank_transfer.html', context)


@login_required
def process_payment(request):
    """Process payment and redirect to payments app"""
    if request.method == 'POST':
        phone = request.POST.get('phone')
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method', 'mpesa')

        # Get user's cart
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            messages.error(request, "Your cart is empty!")
            return redirect('cart:view_cart')

        # Calculate total from cart
        total_amount = cart.get_total()

        # Redirect based on payment method
        if payment_method == 'mpesa':
            # Store cart info in session
            request.session['pending_cart'] = {
                'cart_id': cart.id,
                'total_amount': float(total_amount),
                'phone': phone
            }

            # Redirect to payments app
            return redirect('payments:initiate_mpesa', amount=total_amount, phone=phone)

        elif payment_method == 'cash_on_delivery':
            return redirect('cart:cash_on_delivery')

        elif payment_method == 'bank_transfer':
            return redirect('cart:bank_transfer')

    return redirect('cart:checkout')