# payments/views.py
import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from decimal import Decimal
from django.views.decorators.http import require_POST, require_GET
from django.urls import reverse

# Import models
from .models import Payment, Transaction, Wallet, WalletTransaction
from orders.models import Order

# Setup logger
logger = logging.getLogger(__name__)


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
def wallet_view(request):
    """View wallet balance and transactions"""
    try:
        wallet = Wallet.objects.get(user=request.user)
    except Wallet.DoesNotExist:
        wallet = Wallet.objects.create(user=request.user)

    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-created_at')[:50]

    context = {
        'title': 'My Wallet',
        'wallet': wallet,
        'transactions': transactions,
    }

    return render(request, 'payments/wallet.html', context)


@login_required
@require_POST
def wallet_deposit(request):
    """Deposit money to wallet"""
    try:
        amount = Decimal(request.POST.get('amount', '0'))

        if amount <= 0:
            messages.error(request, "Amount must be greater than 0")
            return redirect('payments:wallet')

        wallet = Wallet.objects.get(user=request.user)

        # For now, just simulate deposit
        # In real implementation, you'd integrate with payment gateway
        wallet.deposit(amount)

        messages.success(request, f"KES {amount} deposited to your wallet")
        return redirect('payments:wallet')

    except Exception as e:
        logger.error(f"Wallet deposit error: {str(e)}")
        messages.error(request, "Failed to process deposit")
        return redirect('payments:wallet')


@login_required
@require_POST
def wallet_withdraw(request):
    """Withdraw money from wallet"""
    try:
        amount = Decimal(request.POST.get('amount', '0'))

        if amount <= 0:
            messages.error(request, "Amount must be greater than 0")
            return redirect('payments:wallet')

        wallet = Wallet.objects.get(user=request.user)

        if not wallet.can_withdraw(amount):
            messages.error(request, "Insufficient balance or withdrawal not allowed")
            return redirect('payments:wallet')

        # Withdraw from wallet
        wallet.withdraw(amount)

        messages.success(request, f"KES {amount} withdrawal requested")
        return redirect('payments:wallet')

    except Exception as e:
        logger.error(f"Wallet withdrawal error: {str(e)}")
        messages.error(request, "Failed to process withdrawal")
        return redirect('payments:wallet')


@login_required
def payment_success(request):
    """Payment success page (generic)"""
    # Try to get last order from session
    order_id = request.session.get('last_order_id')
    order = None

    if order_id:
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            # Clear from session
            del request.session['last_order_id']
            request.session.modified = True
        except Order.DoesNotExist:
            pass

    context = {
        'title': 'Payment Successful',
        'order': order,
    }

    return render(request, 'payments/payment_success.html', context)


@login_required
def payment_failed(request, payment_id=None):
    """Payment failed page (generic)"""
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

        return redirect('cart:checkout')
    else:
        messages.error(request, "Cannot retry payment in current status")
        return redirect('payments:payment_history')


# Transaction History
@login_required
def transaction_history(request):
    """View transaction history"""
    transactions = Transaction.objects.filter(payment__user=request.user).order_by('-created_at')

    context = {
        'title': 'Transaction History',
        'transactions': transactions,
    }

    return render(request, 'payments/transaction_history.html', context)


# Admin views (if needed)
@login_required
def admin_payments(request):
    """Admin view of all payments (for staff users)"""
    if not request.user.is_staff:
        return redirect('dashboard')

    payments = Payment.objects.all().order_by('-created_at')

    context = {
        'title': 'All Payments',
        'payments': payments,
    }

    return render(request, 'payments/admin_payments.html', context)