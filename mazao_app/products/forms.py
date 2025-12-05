# products/forms.py
from django import forms
from .models import Product, Category, ProductReview
from django.utils.text import slugify
from django.core.exceptions import ValidationError
import re


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'price', 'category', 'image',
            'quantity', 'unit', 'location', 'county', 'is_organic',
            'is_fresh', 'min_order_quantity', 'available_from', 'available_until', 'status'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Organic Avocados, Fresh Tomatoes'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your product in detail...'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Price in Ksh',
                'min': '1'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Available quantity',
                'min': '1'
            }),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Specific location/village'
            }),
            'county': forms.Select(attrs={'class': 'form-control'}),
            'is_organic': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_fresh': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'min_order_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Minimum order quantity',
                'min': '1'
            }),
            'available_from': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'available_until': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Customize form fields
        self.fields['category'].queryset = Category.objects.all().order_by('name')

        # Make some fields required
        self.fields['name'].required = True
        self.fields['price'].required = True
        self.fields['category'].required = True
        self.fields['quantity'].required = True
        self.fields['unit'].required = True
        self.fields['county'].required = True

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError("Product name is required.")

        # Generate slug from name
        slug = slugify(name)

        # Check if slug already exists (for new products)
        if self.instance.pk is None:  # New product
            if Product.objects.filter(slug=slug).exists():
                raise ValidationError("A product with a similar name already exists.")

        return name

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price <= 0:
            raise ValidationError("Price must be greater than 0.")
        return price

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than 0.")
        return quantity

    def clean(self):
        cleaned_data = super().clean()
        available_from = cleaned_data.get('available_from')
        available_until = cleaned_data.get('available_until')

        if available_from and available_until:
            if available_until < available_from:
                raise ValidationError("Available until date must be after available from date.")

        return cleaned_data


class ProductSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search for products...'
        })
    )

    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    min_price = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min price'
        })
    )

    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max price'
        })
    )

    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Location/County'
        })
    )

    organic_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Organic Only"
    )

    fresh_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Fresh Only"
    )

    SORT_CHOICES = [
        ('newest', 'Newest First'),
        ('price_asc', 'Price: Low to High'),
        ('price_desc', 'Price: High to Low'),
        ('popular', 'Most Popular'),
    ]

    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='newest',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned_data = super().clean()
        min_price = cleaned_data.get('min_price')
        max_price = cleaned_data.get('max_price')

        if min_price and max_price and min_price > max_price:
            raise ValidationError("Minimum price cannot be greater than maximum price.")

        return cleaned_data


class ProductReviewForm(forms.ModelForm):
    RATING_CHOICES = [
        (5, '★★★★★ - Excellent'),
        (4, '★★★★☆ - Good'),
        (3, '★★★☆☆ - Average'),
        (2, '★★☆☆☆ - Poor'),
        (1, '★☆☆☆☆ - Very Poor'),
    ]

    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label="Your Rating"
    )

    class Meta:
        model = ProductReview
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your experience with this product...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comment'].required = True
        self.fields['rating'].required = True

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        try:
            return int(rating)
        except (ValueError, TypeError):
            raise ValidationError("Please select a valid rating.")

    def clean_comment(self):
        comment = self.cleaned_data.get('comment')
        if len(comment.strip()) < 10:
            raise ValidationError("Please provide a more detailed review (at least 10 characters).")
        return comment