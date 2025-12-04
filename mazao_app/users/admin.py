from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, Profile
from .forms import CustomUserCreationForm, CustomUserChangeForm
# Register your models here.

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    inlines = (ProfileInline,)

    list_display = ('email', 'first_name', 'last_name', 'user_type', 'is_staff', 'is_active', 'is_verified')
    list_filter = ('user_type', 'is_staff', 'is_active', 'is_verified', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'),
         {'fields': ('first_name', 'last_name', 'phone_number', 'user_type', 'location', 'county')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'user_type', 'first_name', 'last_name', 'phone_number'),
        }),
    )

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'farm_name', 'is_complete', 'created_at')
    list_filter = ('user__user_type', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'farm_name')
    raw_id_fields = ('user',)

    fieldsets = (
        (None, {'fields': ('user',)}),
        ('Personal Information', {'fields': ('bio', 'profile_picture', 'date_of_birth')}),
        ('Farmer Information', {'fields': ('farm_name', 'farm_location', 'farm_size', 'crops_grown')}),
        ('Buyer Information', {'fields': ('delivery_address', 'preferred_payment_method')}),
    )