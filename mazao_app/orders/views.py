# orders/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import Order


@login_required
def order_history(request):
    """Display user's order history"""
    # Get all orders for the current user
    orders = Order.objects.filter(buyer=request.user).order_by('-created_at')

    # Calculate summary stats
    total_orders = orders.count()
    total_spent = orders.aggregate(total=Sum('total_amount'))['total'] or 0

    # Group orders by status
    pending_orders = orders.filter(order_status='pending')
    completed_orders = orders.filter(order_status='completed')

    context = {
        'title': 'Order History',
        'orders': orders,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
    }

    return render(request, 'orders/order_history.html', context)


@login_required
def order_list(request):
    """Display user's orders"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'orders': orders,
        'title': 'My Orders'
    }

    return render(request, 'orders/order_list.html', context)