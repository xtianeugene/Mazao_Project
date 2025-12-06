from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid
from decimal import Decimal

CustomUser = get_user_model()


# Payment Status Choices
class PaymentStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    INITIATED = 'initiated', _('Initiated')
    PROCESSING = 'processing', _('Processing')
    SUCCESSFUL = 'successful', _('Successful')
    FAILED = 'failed', _('Failed')
    CANCELLED = 'cancelled', _('Cancelled')


# Transaction Type Choices
class TransactionType(models.TextChoices):
    PAYMENT = 'payment', _('Payment')
    WITHDRAWAL = 'withdrawal', _('Withdrawal')
    REFUND = 'refund', _('Refund')
    COMMISSION = 'commission', _('Commission')


# M-Pesa Transaction Model
class MpesaTransaction(models.Model):
    """Model to track M-Pesa STK Push transactions"""

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='mpesa_transactions')
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])

    # Transaction References
    transaction_ref = models.CharField(max_length=50, unique=True, blank=True)
    checkout_request_id = models.CharField(max_length=100, blank=True)
    merchant_request_id = models.CharField(max_length=100, blank=True, null=True)
    mpesa_receipt = models.CharField(max_length=50, blank=True, null=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    # Response Data
    result_code = models.CharField(max_length=10, blank=True)
    result_desc = models.TextField(blank=True)

    # Order reference
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='mpesa_transactions')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['transaction_ref']),
            models.Index(fields=['checkout_request_id']),
            models.Index(fields=['mpesa_receipt']),
        ]
        verbose_name = 'M-Pesa Transaction'
        verbose_name_plural = 'M-Pesa Transactions'

    def __str__(self):
        return f"M-Pesa {self.transaction_ref} - {self.phone_number} - KES {self.amount}"

    def save(self, *args, **kwargs):
        if not self.transaction_ref:
            self.transaction_ref = f"MPESA{str(uuid.uuid4().int)[:8]}"
        super().save(*args, **kwargs)

    def mark_as_successful(self, mpesa_receipt, result_code='0', result_desc='Success'):
        """Mark transaction as successful"""
        self.status = 'SUCCESS'
        self.mpesa_receipt = mpesa_receipt
        self.result_code = result_code
        self.result_desc = result_desc
        self.completed_at = timezone.now()
        self.save()

    def mark_as_failed(self, result_code, result_desc):
        """Mark transaction as failed"""
        self.status = 'FAILED'
        self.result_code = result_code
        self.result_desc = result_desc
        self.completed_at = timezone.now()
        self.save()

    @property
    def is_successful(self):
        return self.status == 'SUCCESS'

    @property
    def is_pending(self):
        return self.status == 'PENDING'


# Payment Model
class Payment(models.Model):
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    delivery_address = models.TextField(blank=True, null=True)
    delivery_instructions = models.TextField(blank=True, null=True)
    delivery_method = models.CharField(max_length=50, blank=True, null=True)
    cart = models.ForeignKey('cart.Cart', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')

    # Payment Details
    phone_number = models.CharField(max_length=15)
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices, default=TransactionType.PAYMENT)
    description = models.TextField(blank=True)

    # M-Pesa Details
    mpesa_receipt_number = models.CharField(max_length=50, blank=True, null=True, unique=True)
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    merchant_request_id = models.CharField(max_length=100, blank=True, null=True, unique=True)

    # Link to M-Pesa Transaction
    mpesa_transaction = models.OneToOneField(MpesaTransaction, on_delete=models.SET_NULL, null=True, blank=True,
                                             related_name='payment_record')

    # Status Tracking
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    is_complete = models.BooleanField(default=False)

    # Response Data
    result_code = models.IntegerField(null=True, blank=True)
    result_description = models.TextField(blank=True)
    raw_response = models.JSONField(default=dict, blank=True)

    # Metadata
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['mpesa_receipt_number']),
            models.Index(fields=['checkout_request_id']),
        ]

    def __str__(self):
        return f"Payment {self.id} - {self.user.email} - KES {self.amount}"

    @property
    def is_successful(self):
        return self.status == PaymentStatus.SUCCESSFUL

    @property
    def is_pending(self):
        return self.status in [PaymentStatus.PENDING, PaymentStatus.INITIATED, PaymentStatus.PROCESSING]

    def mark_as_successful(self, receipt_number, result_code=0, result_description="Success"):
        """Mark payment as successful"""
        self.status = PaymentStatus.SUCCESSFUL
        self.is_complete = True
        self.mpesa_receipt_number = receipt_number
        self.result_code = result_code
        self.result_description = result_description
        self.completed_at = timezone.now()
        self.save()

    def mark_as_failed(self, result_code, result_description):
        """Mark payment as failed"""
        self.status = PaymentStatus.FAILED
        self.is_complete = True
        self.result_code = result_code
        self.result_description = result_description
        self.completed_at = timezone.now()
        self.save()


# Transaction Model (For internal accounting)
class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.OneToOneField(Payment, on_delete=models.PROTECT, related_name='transaction')

    # Amount breakdown
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    commission = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Reference to order (to be linked when we create orders)
    order_reference = models.CharField(max_length=100, blank=True)
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='transactions')

    # Financial tracking
    is_settled = models.BooleanField(default=False)
    settled_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    notes = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Transaction {self.id} - KES {self.net_amount}"

    def calculate_commission(self):
        """Calculate commission (2.5% of amount)"""
        commission_rate = Decimal('0.025')  # 2.5%
        self.commission = self.amount * commission_rate
        self.net_amount = self.amount - self.commission
        self.save()


# Wallet Model (For user balances)
class Wallet(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Wallet settings
    is_active = models.BooleanField(default=True)
    allow_withdrawals = models.BooleanField(default=True)

    # Security
    pin_hash = models.CharField(max_length=255, blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet - {self.user.email} - KES {self.balance}"

    def deposit(self, amount, payment=None):
        """Deposit money to wallet"""
        self.balance += Decimal(str(amount))
        self.save()

        # Create wallet transaction record
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type='deposit',
            amount=amount,
            payment=payment,
            balance_after=self.balance
        )
        return True

    def withdraw(self, amount, payment=None):
        """Withdraw money from wallet"""
        amount_decimal = Decimal(str(amount))
        if amount_decimal > self.balance:
            raise ValueError("Insufficient balance")

        self.balance -= amount_decimal
        self.save()

        # Create wallet transaction record
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type='withdrawal',
            amount=amount,
            payment=payment,
            balance_after=self.balance
        )
        return True

    def can_withdraw(self, amount):
        """Check if user can withdraw specified amount"""
        return self.is_active and self.allow_withdrawals and Decimal(str(amount)) <= self.balance


# Wallet Transaction Model
class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('commission', 'Commission'),
        ('refund', 'Refund'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)

    # Amount details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)

    # Reference to payment
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='wallet_transactions')

    # Metadata
    description = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Wallet Transaction {self.id} - {self.get_transaction_type_display()} - KES {self.amount}"


# Payment Configuration Model
class PaymentConfig(models.Model):
    """Store M-Pesa API configuration"""

    # API Credentials
    consumer_key = models.CharField(max_length=255)
    consumer_secret = models.CharField(max_length=255)
    business_shortcode = models.CharField(max_length=20)
    passkey = models.CharField(max_length=255)

    # Environment
    ENVIRONMENT_CHOICES = [
        ('sandbox', 'Sandbox'),
        ('production', 'Production'),
    ]
    environment = models.CharField(max_length=20, choices=ENVIRONMENT_CHOICES, default='sandbox')

    # URLs
    callback_url = models.URLField()
    validation_url = models.URLField(blank=True)
    confirmation_url = models.URLField(blank=True)

    # Settings
    transaction_type = models.CharField(max_length=50, default='CustomerPayBillOnline')
    account_reference = models.CharField(max_length=50, default='MAZAO')
    transaction_desc = models.CharField(max_length=100, default='Payment for goods')

    # Commission
    commission_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.025'))  # 2.5%

    # Status
    is_active = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment Configuration'
        verbose_name_plural = 'Payment Configurations'

    def __str__(self):
        return f"M-Pesa Configuration ({self.environment})"

    def save(self, *args, **kwargs):
        # Ensure only one active configuration per environment
        if self.is_active:
            PaymentConfig.objects.filter(environment=self.environment, is_active=True).exclude(pk=self.pk).update(
                is_active=False)
        super().save(*args, **kwargs)

    @property
    def base_url(self):
        """Get base URL based on environment"""
        if self.environment == 'sandbox':
            return 'https://sandbox.safaricom.co.ke'
        return 'https://api.safaricom.co.ke'

    @property
    def auth_url(self):
        """Get authentication URL"""
        return f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"

    @property
    def stk_push_url(self):
        """Get STK Push URL"""
        return f"{self.base_url}/mpesa/stkpush/v1/processrequest"

    @property
    def query_url(self):
        """Get query URL"""
        return f"{self.base_url}/mpesa/stkpushquery/v1/query"