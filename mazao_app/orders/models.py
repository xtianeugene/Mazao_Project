# orders/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from products.models import Product
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
    delivery_address = models.TextField()
    delivery_instructions = models.TextField(blank=True)
    delivery_method = models.CharField(
        max_length=20,
        choices=[('pickup', 'Pickup'), ('delivery', 'Delivery')],
        default='delivery'
    )

    # Payment information
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')

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

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_number} - {self.user.get_full_name() or self.user.username}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate unique order number
            self.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        # Calculate total if not set
        if not self.total_amount:
            self.total_amount = self.subtotal + self.delivery_fee

        super().save(*args, **kwargs)

    @property
    def item_count(self):
        """Get total number of items in order"""
        return sum(item.quantity for item in self.items.all())

    def calculate_totals(self):
        """Calculate order totals from items"""
        self.subtotal = sum(item.total_price for item in self.items.all())
        self.total_amount = self.subtotal + self.delivery_fee
        self.save()


class OrderItem(models.Model):
    """Individual items within an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
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
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tracking')
    status = models.CharField(max_length=50)
    description = models.TextField()
    location = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order.order_number} - {self.status} at {self.created_at}"


class OrderReview(models.Model):
    """Customer reviews for orders"""
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='review')
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Review for Order #{self.order.order_number} - {self.rating} stars"