from django.contrib import admin
from .models import Category, Product, ProductReview, Wishlist

# Register your models here
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'category', 'seller', 'status', 'created_at']
    list_filter = ['category', 'status', 'is_organic', 'is_fresh']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    raw_id_fields = ['seller']

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'created_at']
    list_filter = ['rating']
    search_fields = ['product__name', 'user__email', 'comment']

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__email', 'product__name']