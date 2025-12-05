from django.core.management.base import BaseCommand
from payments.models import PaymentConfig


class Command(BaseCommand):
    help = 'Set up M-Pesa configuration for development'

    def handle(self, *args, **options):
        # Create sandbox configuration
        config, created = PaymentConfig.objects.update_or_create(
            environment='sandbox',
            defaults={
                'consumer_key': 'YOUR_SANDBOX_CONSUMER_KEY',
                'consumer_secret': 'YOUR_SANDBOX_CONSUMER_SECRET',
                'business_shortcode': '174379',
                'passkey': 'YOUR_SANDBOX_PASSKEY',
                'callback_url': 'http://localhost:8000/payments/callback/',
                'account_reference': 'MAZAO',
                'transaction_desc': 'Payment for goods',
                'is_active': True,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('Created M-Pesa sandbox configuration'))
        else:
            self.stdout.write(self.style.SUCCESS('Updated M-Pesa sandbox configuration'))

        self.stdout.write(self.style.SUCCESS('\nM-Pesa Configuration:'))
        self.stdout.write(f"  Environment: {config.environment}")
        self.stdout.write(f"  Business Shortcode: {config.business_shortcode}")
        self.stdout.write(f"  Callback URL: {config.callback_url}")
        self.stdout.write(f"  Active: {config.is_active}")

        self.stdout.write(self.style.WARNING('\n⚠️  IMPORTANT:'))
        self.stdout.write('1. Get your sandbox credentials from: https://developer.safaricom.co.ke/')
        self.stdout.write('2. Update the consumer_key, consumer_secret, and passkey above')
        self.stdout.write('3. For testing, use phone numbers starting with 2547 (Safaricom)')
        self.stdout.write('4. Test amounts should be between 1 and 1000 KES')