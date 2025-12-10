# orders/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid
from decimal import Decimal

User = get_user_model()


class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash on Delivery'),
        ('card', 'Credit Card'),
    ]

    # Order information
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')

    # Delivery information
    delivery_address = models.TextField(blank=True)
    delivery_instructions = models.TextField(blank=True)
    delivery_method = models.CharField(
        max_length=20,
        choices=[('pickup', 'Pickup'), ('delivery', 'Delivery')],
        default='delivery'
    )

    # Payment information
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='mpesa')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')

    # M-Pesa specific fields
    mpesa_receipt = models.CharField(max_length=50, blank=True, null=True)
    mpesa_phone = models.CharField(max_length=15, blank=True, null=True)
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True)
    merchant_request_id = models.CharField(max_length=100, blank=True, null=True)
    transaction_date = models.DateTimeField(null=True, blank=True)

    # Financial information
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Status
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    @property
    def status(self):
        """Alias for order_status for backward compatibility"""
        return self.order_status

    @status.setter
    def status(self, value):
        """Setter for status alias"""
        self.order_status = value

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['order_status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['user']),
            models.Index(fields=['order_number']),
        ]

    def __str__(self):
        return f"Order #{self.order_number} - {self.user.get_full_name() or self.user.username}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate unique order number
            self.order_number = f"ORD{str(uuid.uuid4().int)[:8].upper()}"

        # Generate simpler order number if preferred
        # if not self.order_number:
        #     last_order = Order.objects.all().order_by('-id').first()
        #     if last_order:
        #         last_number = int(last_order.order_number.replace('ORD', ''))
        #         self.order_number = f"ORD{last_number + 1:06d}"
        #     else:
        #         self.order_number = "ORD000001"

        # Calculate total if not set
        if not self.total_amount:
            self.total_amount = self.subtotal + self.delivery_fee

        super().save(*args, **kwargs)

    @property
    def item_count(self):
        """Get total number of items in order"""
        return sum(item.quantity for item in self.items.all())

    @property
    def is_paid(self):
        """Check if order is paid"""
        return self.payment_status in ['paid', 'completed']

    @property
    def is_pending_payment(self):
        """Check if payment is pending"""
        return self.payment_status == 'pending'

    @property
    def can_be_cancelled(self):
        """Check if order can be cancelled"""
        return self.order_status in ['pending', 'processing']

    def calculate_totals(self):
        """Calculate order totals from items"""
        self.subtotal = sum(item.total_price for item in self.items.all())
        self.total_amount = self.subtotal + self.delivery_fee
        self.save()

    def mark_as_paid(self, mpesa_receipt=None, mpesa_phone=None, checkout_request_id=None):
        """Mark order as paid"""
        self.payment_status = 'paid'
        if mpesa_receipt:
            self.mpesa_receipt = mpesa_receipt
        if mpesa_phone:
            self.mpesa_phone = mpesa_phone
        if checkout_request_id:
            self.checkout_request_id = checkout_request_id
        self.transaction_date = timezone.now()
        self.save()

    def mark_as_processing(self):
        """Mark order as processing"""
        self.order_status = 'processing'
        self.save()

    def mark_as_completed(self):
        """Mark order as completed"""
        self.order_status = 'completed'
        self.payment_status = 'completed'
        self.completed_at = timezone.now()
        self.save()

    def mark_as_cancelled(self):
        """Mark order as cancelled"""
        self.order_status = 'cancelled'
        self.save()

    def get_status_display(self):
        """Get human-readable status"""
        return dict(self.ORDER_STATUS_CHOICES).get(self.order_status, self.order_status.capitalize())

    def get_payment_status_display(self):
        """Get human-readable payment status"""
        return dict(self.PAYMENT_STATUS_CHOICES).get(self.payment_status, self.payment_status.capitalize())

    def get_payment_method_display(self):
        """Get human-readable payment method"""
        return dict(self.PAYMENT_METHOD_CHOICES).get(self.payment_method, self.payment_method.capitalize())

    def get_delivery_method_display(self):
        """Get human-readable delivery method"""
        delivery_choices = dict([('pickup', 'Pickup'), ('delivery', 'Home Delivery')])
        return delivery_choices.get(self.delivery_method, self.delivery_method.capitalize())

    def get_order_items_summary(self):
        """Get summary of order items"""
        items = self.items.all()
        if not items:
            return "No items"

        first_item = items.first()
        item_count = items.count()

        if item_count == 1:
            return f"{first_item.product.name}"
        else:
            return f"{first_item.product.name} + {item_count - 1} more item{'s' if item_count > 2 else ''}"

    def get_formatted_order_number(self):
        """Get formatted order number for display"""
        if self.order_number.startswith('ORD'):
            return f"#{self.order_number.replace('ORD', '')}"
        return f"#{self.order_number}"


class OrderItem(models.Model):
    """Individual items within an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='order_items')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Additional details
    delivery_method = models.CharField(
        max_length=20,
        choices=[('pickup', 'Pickup'), ('delivery', 'Delivery')],
        default='pickup'
    )
    special_instructions = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        unique_together = ['order', 'product']

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Order #{self.order.order_number})"

    @property
    def total_price(self):
        """Calculate total price for this item"""
        return Decimal(str(self.quantity)) * self.unit_price

    @property
    def get_delivery_method_display(self):
        """Get human-readable delivery method"""
        return dict([('pickup', 'Pickup'), ('delivery', 'Delivery')]).get(self.delivery_method, self.delivery_method)

    def save(self, *args, **kwargs):
        # Set unit price from product if not set
        if not self.unit_price:
            self.unit_price = self.product.price

        super().save(*args, **kwargs)

        # Update order totals
        if self.order:
            self.order.calculate_totals()


class OrderTracking(models.Model):
    """Track order status changes"""
    TRACKING_STATUS_CHOICES = [
        ('order_placed', 'Order Placed'),
        ('payment_received', 'Payment Received'),
        ('order_confirmed', 'Order Confirmed'),
        ('preparing', 'Preparing Order'),
        ('ready_for_pickup', 'Ready for Pickup'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tracking')
    status = models.CharField(max_length=50, choices=TRACKING_STATUS_CHOICES)
    description = models.TextField()
    location = models.CharField(max_length=255, blank=True)
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order.order_number} - {self.get_status_display()} at {self.created_at}"

    def get_status_display(self):
        """Get human-readable tracking status"""
        return dict(self.TRACKING_STATUS_CHOICES).get(self.status, self.status.replace('_', ' ').title())


class OrderReview(models.Model):
    """Customer reviews for orders"""
    RATING_CHOICES = [
        (1, '★☆☆☆☆ - Poor'),
        (2, '★★☆☆☆ - Fair'),
        (3, '★★★☆☆ - Good'),
        (4, '★★★★☆ - Very Good'),
        (5, '★★★★★ - Excellent'),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='review')
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Review for Order #{self.order.order_number} - {self.rating} stars"

    @property
    def star_rating(self):
        """Get star rating as HTML"""
        stars = '★' * self.rating + '☆' * (5 - self.rating)
        return stars

    @property
    def get_rating_display(self):
        """Get human-readable rating"""
        return dict(self.RATING_CHOICES).get(self.rating, f'{self.rating} stars')