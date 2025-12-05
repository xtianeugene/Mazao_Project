from django import forms
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import re


class PaymentForm(forms.Form):
    amount = forms.DecimalField(
        label=_('Amount (KES)'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('1.00'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount',
            'min': '1',
            'step': '0.01'
        })
    )

    phone_number = forms.CharField(
        label=_('M-Pesa Phone Number'),
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '07XXXXXXXX or 2547XXXXXXXX'
        })
    )

    description = forms.CharField(
        label=_('Payment Description'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Optional description'
        })
    )

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')

        # Remove any spaces or special characters
        phone_number = re.sub(r'[^\d]', '', phone_number)

        if not phone_number:
            raise forms.ValidationError("Phone number is required")

        # Check length
        if len(phone_number) not in [9, 10, 12]:
            raise forms.ValidationError("Invalid phone number length")

        # Format to 254 format
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif len(phone_number) == 9:
            phone_number = '254' + phone_number
        elif phone_number.startswith('254') and len(phone_number) == 12:
            pass  # Already in correct format
        else:
            raise forms.ValidationError("Invalid phone number format")

        # Check if it's a Safaricom number
        if not phone_number.startswith('2547'):
            raise forms.ValidationError("Only Safaricom numbers are supported")

        return phone_number

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')

        if amount < Decimal('1.00'):
            raise forms.ValidationError("Minimum amount is KES 1.00")

        if amount > Decimal('150000.00'):
            raise forms.ValidationError("Maximum amount is KES 150,000.00")

        return amount


class WithdrawalForm(forms.Form):
    amount = forms.DecimalField(
        label=_('Withdrawal Amount (KES)'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('100.00'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount to withdraw',
            'min': '100',
            'step': '0.01'
        })
    )

    phone_number = forms.CharField(
        label=_('M-Pesa Phone Number'),
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '07XXXXXXXX or 2547XXXXXXXX'
        })
    )

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')

        if amount < Decimal('100.00'):
            raise forms.ValidationError("Minimum withdrawal is KES 100.00")

        if amount > Decimal('70000.00'):
            raise forms.ValidationError("Maximum withdrawal per transaction is KES 70,000.00")

        return amount


class QuickPaymentForm(forms.Form):
    """Form for quick payments from product pages"""
    phone_number = forms.CharField(
        label=_('M-Pesa Phone Number'),
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '07XXXXXXXX or 2547XXXXXXXX',
            'id': 'quick-payment-phone'
        })
    )

    def __init__(self, *args, **kwargs):
        self.amount = kwargs.pop('amount', None)
        super().__init__(*args, **kwargs)

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')

        # Remove any spaces or special characters
        phone_number = re.sub(r'[^\d]', '', phone_number)

        if not phone_number:
            raise forms.ValidationError("Phone number is required")

        # Check length
        if len(phone_number) not in [9, 10, 12]:
            raise forms.ValidationError("Invalid phone number length")

        # Format to 254 format
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif len(phone_number) == 9:
            phone_number = '254' + phone_number
        elif phone_number.startswith('254') and len(phone_number) == 12:
            pass  # Already in correct format
        else:
            raise forms.ValidationError("Invalid phone number format")

        # Check if it's a Safaricom number
        if not phone_number.startswith('2547'):
            raise forms.ValidationError("Only Safaricom numbers are supported")

        return phone_number


class PaymentConfigForm(forms.ModelForm):
    class Meta:
        from .models import PaymentConfig
        model = PaymentConfig
        fields = '__all__'
        widgets = {
            'consumer_key': forms.TextInput(attrs={'class': 'form-control'}),
            'consumer_secret': forms.TextInput(attrs={'class': 'form-control'}),
            'business_shortcode': forms.TextInput(attrs={'class': 'form-control'}),
            'passkey': forms.TextInput(attrs={'class': 'form-control'}),
            'callback_url': forms.URLInput(attrs={'class': 'form-control'}),
            'validation_url': forms.URLInput(attrs={'class': 'form-control'}),
            'confirmation_url': forms.URLInput(attrs={'class': 'form-control'}),
            'environment': forms.Select(attrs={'class': 'form-select'}),
            'transaction_type': forms.TextInput(attrs={'class': 'form-control'}),
            'account_reference': forms.TextInput(attrs={'class': 'form-control'}),
            'transaction_desc': forms.TextInput(attrs={'class': 'form-control'}),
            'commission_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }