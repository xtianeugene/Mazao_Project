# cart/forms.py
from django import forms
from django.core.validators import MinValueValidator
from decimal import Decimal


class CartItemForm(forms.Form):
    """Form for adding items to cart"""
    quantity = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0.01',
            'step': '0.01',
            'placeholder': 'Quantity'
        })
    )

    delivery_method = forms.ChoiceField(
        choices=[
            ('pickup', 'Pickup'),
            ('delivery', 'Delivery')
        ],
        initial='pickup',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )

    special_instructions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Any special instructions...'
        })
    )

    def clean_quantity(self):
        """Validate quantity"""
        quantity = self.cleaned_data['quantity']
        if quantity <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")
        return quantity


class CheckoutForm(forms.Form):
    PAYMENT_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('cash', 'Cash on Delivery'),
        ('bank', 'Bank Transfer'),
    ]

    delivery_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter your delivery address'
        }),
        required=True,
        label="Delivery Address"
    )

    delivery_instructions = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Any special delivery instructions...'
        }),
        required=False,
        label="Delivery Instructions (Optional)"
    )

    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=True,
        label="Payment Method"
    )

    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '07XXXXXXXX'
        }),
        label="Phone Number (for M-Pesa)",
        help_text="Required for M-Pesa payments"
    )

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        phone_number = cleaned_data.get('phone_number')

        if payment_method == 'mpesa' and not phone_number:
            self.add_error('phone_number', 'Phone number is required for M-Pesa payments')

        return cleaned_data