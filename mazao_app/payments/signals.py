from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Wallet

CustomUser = get_user_model()

@receiver(post_save, sender=CustomUser)
def create_user_wallet(sender, instance, created, **kwargs):
    """Create a wallet for new users"""
    if created:
        Wallet.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_user_wallet(sender, instance, **kwargs):
    """Save user's wallet"""
    if hasattr(instance, 'wallet'):
        instance.wallet.save()