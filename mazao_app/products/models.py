# products/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.urls import reverse
import os
from datetime import date

User = get_user_model()


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    # Define the choices classes FIRST, before using them
    class ProductStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        OUT_OF_STOCK = 'out_of_stock', 'Out of Stock'
        DISCONTINUED = 'discontinued', 'Discontinued'

    class UnitChoices(models.TextChoices):
        KG = 'kg', 'Kilogram'
        G = 'g', 'Gram'
        L = 'l', 'Liter'
        ML = 'ml', 'Milliliter'
        PIECE = 'piece', 'Piece'
        BUNCH = 'bunch', 'Bunch'
        DOZEN = 'dozen', 'Dozen'

    COUNTY_CHOICES = [
        ('', 'Select County'),
        ('nairobi', 'Nairobi'),
        ('mombasa', 'Mombasa'),
        ('kisumu', 'Kisumu'),
        ('nakuru', 'Nakuru'),
        ('eldoret', 'Eldoret'),
        ('thika', 'Thika'),
        ('kakamega', 'Kakamega'),
        ('kisii', 'Kisii'),
        ('nyeri', 'Nyeri'),
        ('meru', 'Meru'),
        ('machakos', 'Machakos'),
        ('kitui', 'Kitui'),
        ('embu', 'Embu'),
        ('kirinyaga', 'Kirinyaga'),
        ('muranga', 'Muranga'),
        ('kiambu', 'Kiambu'),
        ('bungoma', 'Bungoma'),
        ('busia', 'Busia'),
        ('homa_bay', 'Homa Bay'),
        ('migori', 'Migori'),
        ('siaya', 'Siaya'),
        ('vihiga', 'Vihiga'),
        ('baringo', 'Baringo'),
        ('bomet', 'Bomet'),
        ('elgeyo_marakwet', 'Elgeyo-Marakwet'),
        ('garissa', 'Garissa'),
        ('kilifi', 'Kilifi'),
        ('kwale', 'Kwale'),
        ('lamu', 'Lamu'),
        ('mandera', 'Mandera'),
        ('marsabit', 'Marsabit'),
        ('narok', 'Narok'),
        ('nyamira', 'Nyamira'),
        ('nyandarua', 'Nyandarua'),
        ('nandi', 'Nandi'),
        ('samburu', 'Samburu'),
        ('taita_taveta', 'Taita-Taveta'),
        ('tana_river', 'Tana River'),
        ('trans_nzoia', 'Trans Nzoia'),
        ('turkana', 'Turkana'),
        ('uasin_gishu', 'Uasin Gishu'),
        ('wajir', 'Wajir'),
        ('west_pokot', 'West Pokot'),
    ]

    # Basic info
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()

    # Pricing and quantity
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    unit = models.CharField(max_length=20, choices=UnitChoices.choices)
    min_order_quantity = models.PositiveIntegerField(default=1)

    # Category and seller
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')

    # Location
    location = models.CharField(max_length=255, blank=True)
    county = models.CharField(
        max_length=50,
        choices=COUNTY_CHOICES,
        blank=True,
        null=True
    )

    # Product attributes
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_organic = models.BooleanField(default=False)
    is_fresh = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)

    # Availability
    available_from = models.DateField(null=True, blank=True)
    available_until = models.DateField(null=True, blank=True)

    # Status and tracking - MOVED OUTSIDE THE ProductStatus CLASS
    status = models.CharField(
        max_length=20,
        choices=ProductStatus.choices,
        default=ProductStatus.ACTIVE
    )
    views = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})

    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])


class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['product', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.product.name} ({self.rating} stars)"


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'product']
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.email} - {self.product.name}"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'created_at']

    def __str__(self):
        return f"Image for {self.product.name}"