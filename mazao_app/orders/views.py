# orders/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Order, OrderItem


@login_required
def my_orders(request):
    """Display all orders for the logged-in user"""
    # Get orders for the current user
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    # FIXED: Use 'order_status' instead of 'status'
    pending_count = orders.filter(order_status='pending').count()
    processing_count = orders.filter(order_status='processing').count()
    completed_count = orders.filter(order_status='completed').count()
    cancelled_count = orders.filter(order_status='cancelled').count()

    context = {
        'orders': orders,
        'pending_count': pending_count,
        'processing_count': processing_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'total_orders': orders.count(),
    }

    return render(request, 'orders/my_orders.html', context)


@login_required
def order_detail(request, order_id):
    """Display details of a specific order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order)

    context = {
        'order': order,
        'order_items': order_items,
    }

    return render(request, 'orders/order_detail.html', context)