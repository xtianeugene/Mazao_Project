# payments/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Wallet, MpesaTransaction, Payment, TransactionType, PaymentStatus

CustomUser = get_user_model()


@receiver(post_save, sender=CustomUser)
def create_user_wallet(sender, instance, created, **kwargs):
    """Create a wallet for new users"""
    if created:
        Wallet.objects.create(user=instance)


@receiver(post_save, sender=MpesaTransaction)
def create_payment_from_mpesa(sender, instance, created, **kwargs):
    """Create a Payment record when M-Pesa transaction is successful"""
    if instance.is_successful and not hasattr(instance, 'payment_record'):
        Payment.objects.create(
            user=instance.user,
            amount=instance.amount,
            phone_number=instance.phone_number,
            transaction_type=TransactionType.PAYMENT,
            description=f"M-Pesa Payment - {instance.transaction_ref}",
            mpesa_receipt_number=instance.mpesa_receipt,
            checkout_request_id=instance.checkout_request_id,
            merchant_request_id=instance.merchant_request_id,
            mpesa_transaction=instance,
            status=PaymentStatus.SUCCESSFUL,
            is_complete=True,
            result_code=0,
            result_description=instance.result_desc,
            completed_at=instance.completed_at
        )