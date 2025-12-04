from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from .models import Profile, UserType
from django.contrib.auth.forms import AuthenticationForm

CustomUser = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'})
    )
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'})
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'})
    )
    user_type = forms.ChoiceField(
        choices=UserType.choices,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial=UserType.BUYER
    )

    class Meta:
        model = CustomUser
        fields = ('email', 'user_type', 'first_name', 'last_name', 'phone_number')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+254712345678'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email


class FarmerRegistrationForm(forms.ModelForm):
    farm_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your farm name'})
    )
    farm_location = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Farm location'})
    )
    farm_size = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Farm size in acres'})
    )
    crops_grown = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'List crops you grow', 'rows': 3})
    )

    class Meta:
        model = Profile
        fields = ('farm_name', 'farm_location', 'farm_size', 'crops_grown')


class BuyerRegistrationForm(forms.ModelForm):
    delivery_address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Your delivery address', 'rows': 3})
    )

    class Meta:
        model = Profile
        fields = ('delivery_address',)


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'phone_number', 'location', 'county')


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('bio', 'profile_picture', 'date_of_birth', 'farm_name', 'farm_location', 'farm_size', 'crops_grown',
                  'delivery_address')
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'farm_name': forms.TextInput(attrs={'class': 'form-control'}),
            'farm_location': forms.TextInput(attrs={'class': 'form-control'}),
            'farm_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'crops_grown': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'delivery_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)