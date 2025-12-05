from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager  # Change import
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
import os
from datetime import date


# User Types
class UserType(models.TextChoices):
    FARMER = 'farmer', _('Farmer')
    BUYER = 'buyer', _('Buyer')


# Custom User Manager - FIXED
class CustomUserManager(BaseUserManager):  # Inherit from BaseUserManager
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

    # ADD THIS METHOD
    def get_by_natural_key(self, username):
        return self.get(**{self.model.USERNAME_FIELD: username})


# Custom User Model
class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)

    # Additional fields
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+254712345678'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        null=True
    )
    user_type = models.CharField(
        max_length=10,
        choices=UserType.choices,
        default=UserType.BUYER
    )
    location = models.CharField(max_length=255, blank=True, null=True)
    county = models.CharField(max_length=100, blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    # Set email as the unique identifier
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return self.email

    @property
    def is_farmer(self):
        return self.user_type == UserType.FARMER

    @property
    def is_buyer(self):
        return self.user_type == UserType.BUYER

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email


# User Profile Model
def profile_picture_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/users/user_<id>/<filename>
    ext = filename.split('.')[-1]
    filename = f"profile_{instance.user.id}_{date.today()}.{ext}"
    return os.path.join('users', f'user_{instance.user.id}', filename)


class Profile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True)
    profile_picture = models.ImageField(upload_to=profile_picture_path, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    # Farmer-specific fields
    farm_name = models.CharField(max_length=255, blank=True, null=True)
    farm_location = models.CharField(max_length=255, blank=True, null=True)
    farm_size = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    crops_grown = models.TextField(blank=True, null=True)

    # Buyer-specific fields
    delivery_address = models.TextField(blank=True, null=True)
    preferred_payment_method = models.CharField(max_length=50, blank=True, null=True)

    # Common fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.email}"

    @property
    def address(self):
        """Get address from available fields"""
        # Try different field names
        if hasattr(self, 'location') and self.location:
            return self.location
        elif hasattr(self, 'county') and self.county:
            return self.county
        elif hasattr(self, 'shipping_address') and self.shipping_address:
            return self.shipping_address
        elif hasattr(self, 'physical_address') and self.physical_address:
            return self.physical_address
        else:
            return ''

    @property
    def is_complete(self):
        """Check if profile is complete based on user type"""
        if self.user.is_farmer:
            return all([self.farm_name, self.farm_location, self.crops_grown])
        elif self.user.is_buyer:
            return bool(self.delivery_address)
        return True