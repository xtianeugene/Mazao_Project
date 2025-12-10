# orders/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils import timezone
from django.http import JsonResponse
import json
from datetime import datetime, timedelta
from .models import Order, OrderItem


@login_required
def my_orders(request):
    """Display all orders for the logged-in user"""
    # Get orders for the current user
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    # Calculate statistics
    total_spent = orders.aggregate(total=Sum('total_amount'))['total'] or 0

    # Use the correct field name from your Order model
    # If your model has 'status' field, use that. If it has 'order_status', use that.
    # Let's check both possibilities:
    try:
        # Try with 'status' field
        pending_count = orders.filter(status='pending').count()
        processing_count = orders.filter(status='processing').count()
        completed_count = orders.filter(status='completed').count()
        cancelled_count = orders.filter(status='cancelled').count()
    except:
        # Try with 'order_status' field
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
        'total_spent': total_spent,
        'title': 'My Orders'
    }

    return render(request, 'orders/my_orders.html', context)


@login_required
def order_detail(request, order_id):
    """Display details of a specific order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order)

    # Calculate subtotal
    subtotal = sum(item.total_price for item in order_items)

    context = {
        'order': order,
        'order_items': order_items,
        'subtotal': subtotal,
        'title': f'Order #{order.order_number}'
    }

    return render(request, 'orders/order_detail.html', context)


@login_required
def order_list(request):
    """View all orders (for farmers) or user orders (for buyers)"""

    if request.user.is_farmer:
        # For farmers: Show all orders for their products
        orders = Order.objects.filter(
            items__product__farmer=request.user
        ).distinct().order_by('-created_at')

        # Filter by status if provided
        status_filter = request.GET.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)
    else:
        # For buyers: Show their own orders
        orders = Order.objects.filter(
            user=request.user
        ).order_by('-created_at')

    # Calculate statistics
    total_revenue = orders.aggregate(total=Sum('total_amount'))['total'] or 0

    # Use the correct field name based on your model
    try:
        pending_count = orders.filter(status='pending').count()
    except:
        pending_count = orders.filter(order_status='pending').count()

    # This month's orders
    this_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month_count = orders.filter(created_at__gte=this_month_start).count()

    context = {
        'orders': orders,
        'total_revenue': total_revenue,
        'pending_count': pending_count,
        'this_month_count': this_month_count,
        'title': 'Order List' if request.user.is_farmer else 'My Orders'
    }

    return render(request, 'orders/order_list.html', context)


@login_required
def cancel_order(request, order_id):
    """Cancel an order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Check if order can be cancelled (only pending orders)
    if hasattr(order, 'status'):
        if order.status != 'pending':
            messages.error(request, "Only pending orders can be cancelled.")
            return redirect('my_orders')
    elif hasattr(order, 'order_status'):
        if order.order_status != 'pending':
            messages.error(request, "Only pending orders can be cancelled.")
            return redirect('my_orders')

    if request.method == 'POST':
        reason = request.POST.get('reason', 'No reason provided')

        # Update order status
        if hasattr(order, 'status'):
            order.status = 'cancelled'
        elif hasattr(order, 'order_status'):
            order.order_status = 'cancelled'

        order.save()

        messages.success(request, f"Order #{order.order_number} has been cancelled.")
        return redirect('my_orders')

    # If GET request, show confirmation page
    context = {
        'order': order,
        'title': 'Cancel Order'
    }
    return render(request, 'orders/cancel_order.html', context)


@login_required
def update_order_status(request, order_id):
    """Update order status (for farmers only)"""
    if not request.user.is_farmer:
        messages.error(request, "Only farmers can update order status.")
        return redirect('my_orders')

    order = get_object_or_404(Order, id=order_id)

    # Verify the order contains farmer's products
    if not order.items.filter(product__farmer=request.user).exists():
        messages.error(request, "You can only update orders for your products.")
        return redirect('order_list')

    if request.method == 'POST':
        new_status = request.POST.get('status')

        if new_status:
            # Validate status
            valid_statuses = ['pending', 'processing', 'confirmed', 'shipping', 'delivered', 'cancelled']
            if new_status in valid_statuses:
                if hasattr(order, 'status'):
                    order.status = new_status
                elif hasattr(order, 'order_status'):
                    order.order_status = new_status

                order.save()
                messages.success(request, f"Order status updated to {new_status}.")
            else:
                messages.error(request, "Invalid order status.")

        return redirect('order_list')

    context = {
        'order': order,
        'title': 'Update Order Status'
    }
    return render(request, 'orders/update_status.html', context)


@login_required
def track_order(request, order_id):
    """Track order delivery status"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Mock tracking data - in a real app, this would come from a shipping API
    tracking_data = [
        {
            'status': 'Order Placed',
            'date': order.created_at,
            'location': 'Online Store',
            'description': 'Your order has been placed successfully.'
        },
        {
            'status': 'Processing',
            'date': order.created_at + timedelta(hours=1),
            'location': 'Warehouse',
            'description': 'Order is being prepared for shipping.'
        },
        {
            'status': 'Shipped',
            'date': order.created_at + timedelta(days=1),
            'location': 'Shipping Center',
            'description': 'Order has been shipped.'
        },
        {
            'status': 'Out for Delivery',
            'date': order.created_at + timedelta(days=2),
            'location': 'Local Delivery Center',
            'description': 'Order is out for delivery.'
        },
        {
            'status': 'Delivered',
            'date': order.created_at + timedelta(days=3),
            'location': 'Your Address',
            'description': 'Order has been delivered.'
        }
    ]

    # Filter based on current order status
    status_mapping = {
        'pending': 0,
        'processing': 1,
        'confirmed': 1,
        'shipping': 2,
        'delivered': 4,
        'cancelled': 0
    }

    current_status = order.status if hasattr(order, 'status') else order.order_status
    current_step = status_mapping.get(current_status, 0)

    context = {
        'order': order,
        'tracking_data': tracking_data,
        'current_step': current_step,
        'title': f'Track Order #{order.order_number}'
    }

    return render(request, 'orders/track_order.html', context)


@login_required
def download_invoice(request, order_id):
    """Generate and download order invoice"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order)

    # Calculate totals
    subtotal = sum(item.total_price for item in order_items)
    shipping = getattr(order, 'shipping_cost', 0) or 0
    tax = getattr(order, 'tax_amount', 0) or 0
    total = order.total_amount

    context = {
        'order': order,
        'order_items': order_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'tax': tax,
        'total': total,
        'invoice_date': timezone.now().date(),
        'invoice_number': f"INV-{order.order_number}",
    }

    return render(request, 'orders/invoice.html', context)


@login_required
def repeat_order(request, order_id):
    """Repeat a previous order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order)

    # Add items to cart (you'll need a cart system)
    # This is a simplified version - you'll need to adapt to your cart system

    messages.success(request, f"Items from order #{order.order_number} have been added to your cart.")
    return redirect('view_cart')  # Replace with your cart URL


@login_required
def order_statistics(request):
    """Get order statistics for dashboard"""
    if request.user.is_farmer:
        orders = Order.objects.filter(
            items__product__farmer=request.user
        ).distinct()
    else:
        orders = Order.objects.filter(user=request.user)

    # Get status field name
    status_field = 'status' if hasattr(Order, 'status') else 'order_status'

    # Monthly statistics
    monthly_stats = []
    for i in range(6):
        month_start = timezone.now().replace(day=1) - timedelta(days=30 * i)
        month_end = month_start.replace(day=1) + timedelta(days=31)
        month_orders = orders.filter(
            created_at__gte=month_start,
            created_at__lt=month_end
        )

        monthly_stats.append({
            'month': month_start.strftime('%b %Y'),
            'count': month_orders.count(),
            'revenue': month_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        })

    # Status breakdown
    status_counts = {}
    for status_choice in Order._meta.get_field(status_field).choices:
        status_code = status_choice[0]
        count = orders.filter(**{status_field: status_code}).count()
        if count > 0:
            status_counts[status_choice[1]] = count

    return JsonResponse({
        'monthly_stats': monthly_stats,
        'status_counts': status_counts,
        'total_orders': orders.count(),
        'total_revenue': orders.aggregate(total=Sum('total_amount'))['total'] or 0,
        'average_order_value': orders.aggregate(avg=Sum('total_amount'))[
                                   'avg'] / orders.count() if orders.count() > 0 else 0
    })