from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView
from django.contrib.auth.views import LoginView as AuthLoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from .models import CustomUser, Profile, UserType
from .forms import (
    CustomUserCreationForm, FarmerRegistrationForm,
    BuyerRegistrationForm, ProfileUpdateForm, LoginForm
)
from cart.models import Cart, CartItem
from orders.models import Order, OrderItem
from django.db.models import Sum, Count
from products.models import Product


# Create your views here.

# Custom Login View
class LoginView(AuthLoginView):
    template_name = 'users/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        messages.success(self.request, f"Welcome back, {self.request.user.first_name}!")
        return super().get_success_url()

    # ADD THESE METHODS FOR DEBUGGING:
    def form_valid(self, form):
        print("=== LOGIN DEBUG ===")
        print("Form is valid:", form.is_valid())
        print("Cleaned data:", form.cleaned_data)

        # Try to authenticate manually
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')
        print(f"Email: {email}, Password: {password}")

        # Check if user exists
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
            print(f"User found: {user.email}, is_active: {user.is_active}")
        except User.DoesNotExist:
            print("User not found with this email")

        # Call parent method
        return super().form_valid(form)

    def form_invalid(self, form):
        print("=== LOGIN FAILED ===")
        print("Form errors:", form.errors)
        return super().form_invalid(form)


# Registration View
def register_view(request):
    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST)

        if user_form.is_valid():
            user = user_form.save()

            # Auto-login after registration
            login(request, user)
            messages.success(request, f"Account created successfully! Welcome {user.first_name}!")

            # Redirect to appropriate profile completion page
            if user.user_type == UserType.FARMER:
                return redirect('complete_farmer_profile')
            else:
                return redirect('complete_buyer_profile')
    else:
        user_form = CustomUserCreationForm()

    return render(request, 'users/register.html', {
        'user_form': user_form,
    })


# Complete Farmer Profile
@login_required
def complete_farmer_profile(request):
    if not request.user.is_farmer:
        return redirect('home')

    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)

    if request.method == 'POST':
        form = FarmerRegistrationForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Farmer profile completed successfully!")
            return redirect('profile')
    else:
        form = FarmerRegistrationForm(instance=profile)

    return render(request, 'users/complete_farmer_profile.html', {
        'form': form,
    })


# Complete Buyer Profile
@login_required
def complete_buyer_profile(request):
    if not request.user.is_buyer:
        return redirect('home')

    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)

    if request.method == 'POST':
        form = BuyerRegistrationForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Buyer profile completed successfully!")
            return redirect('profile')
    else:
        form = BuyerRegistrationForm(instance=profile)

    return render(request, 'users/complete_buyer_profile.html', {
        'form': form,
    })


# Profile View
@login_required
def profile_view(request):
    profile = get_object_or_404(Profile, user=request.user)

    context = {
        'profile': profile,
        'user': request.user,
    }

    return render(request, 'users/profile.html', context)


# Profile Update View
@login_required
def profile_update_view(request):
    profile = get_object_or_404(Profile, user=request.user)

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=profile)

    return render(request, 'users/profile_update.html', {
        'form': form,
        'profile': profile,
    })


# Custom Logout View
def custom_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')


# Dashboard View
@login_required
def dashboard_view(request):
    user = request.user
    context = {'user': user}

    # Add cart data for buyers
    if user.is_buyer:
        try:
            cart = Cart.objects.get(user=user)
            cart_items = CartItem.objects.filter(cart=cart)
            cart_items_count = cart_items.count()
            cart_total = sum(item.total_price for item in cart_items)
        except Cart.DoesNotExist:
            cart_items_count = 0
            cart_total = 0

        # Calculate buyer stats from Order model
        # CHANGED: Use 'user' instead of 'buyer'
        total_orders = Order.objects.filter(user=user).count()
        pending_orders = Order.objects.filter(
            user=user,  # CHANGED
            order_status='pending'
        ).count()
        completed_orders = Order.objects.filter(
            user=user,  # CHANGED
            order_status='completed'
        ).count()

        # Calculate total spent (sum of completed orders)
        total_spent_result = Order.objects.filter(
            user=user,  # CHANGED
            order_status='completed'
        ).aggregate(total_spent=Sum('total_amount'))
        total_spent = total_spent_result['total_spent'] or 0

        # Get recent orders
        recent_orders = Order.objects.filter(user=user).order_by('-created_at')[:5]  # CHANGED

        context.update({
            'cart_items_count': cart_items_count,
            'cart_total': cart_total,
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'completed_orders': completed_orders,
            'total_spent': total_spent,
            'recent_orders': recent_orders,
        })

    # Add farmer stats
    elif user.is_farmer:
        # Get farmer's products
        products = Product.objects.filter(seller=user)
        total_products = products.count()
        active_products = products.filter(status='active').count()
        out_of_stock = products.filter(status='out_of_stock').count()

        # Get orders for farmer's products
        # CHANGED: Get orders through OrderItem since Order now has multiple products
        farmer_order_items = OrderItem.objects.filter(product__seller=user)
        total_orders_count = Order.objects.filter(
            items__product__seller=user
        ).distinct().count()

        # Get unique customers
        unique_customers = Order.objects.filter(
            items__product__seller=user
        ).values('user').distinct().count()

        # Calculate total earnings (sum of completed orders for farmer's products)
        total_earnings_result = Order.objects.filter(
            items__product__seller=user,
            order_status='completed'
        ).distinct().aggregate(total_earnings=Sum('total_amount'))
        total_earnings = total_earnings_result['total_earnings'] or 0

        # Get recent orders for farmer's products
        recent_orders = Order.objects.filter(
            items__product__seller=user
        ).distinct().order_by('-created_at')[:5]

        # Get pending orders count
        pending_orders = Order.objects.filter(
            items__product__seller=user,
            order_status='pending'
        ).distinct().count()

        # Get product views
        total_views = products.aggregate(total_views=Sum('views'))['total_views'] or 0

        context.update({
            'total_products': total_products,
            'active_products': active_products,
            'out_of_stock': out_of_stock,
            'total_orders': total_orders_count,
            'pending_orders': pending_orders,
            'unique_customers': unique_customers,
            'total_earnings': total_earnings,
            'total_views': total_views,
            'recent_orders': recent_orders,
            'products': products[:5],  # Recent products
        })

    return render(request, 'users/dashboard.html', context)


# Additional Views

@login_required
def my_orders(request):
    """View for users to see their orders"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')  # CHANGED

    context = {
        'orders': orders,
    }
    return render(request, 'users/my_orders.html', context)


@login_required
def order_detail(request, order_id):
    """View order details"""
    order = get_object_or_404(Order, id=order_id, user=request.user)  # CHANGED
    order_items = order.items.all()

    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'users/order_detail.html', context)


@login_required
def farmer_orders(request):
    """View for farmers to see orders for their products"""
    if not request.user.is_farmer:
        messages.error(request, "Only farmers can access this page.")
        return redirect('dashboard')

    # Get orders that contain farmer's products
    orders = Order.objects.filter(
        items__product__seller=request.user
    ).distinct().order_by('-created_at')

    context = {
        'orders': orders,
    }
    return render(request, 'users/farmer_orders.html', context)


@login_required
def farmer_order_detail(request, order_id):
    """View for farmers to see order details"""
    if not request.user.is_farmer:
        messages.error(request, "Only farmers can access this page.")
        return redirect('dashboard')

    order = get_object_or_404(Order, id=order_id)

    # Check if this order contains farmer's products
    if not order.items.filter(product__seller=request.user).exists():
        messages.error(request, "You can only view orders for your products.")
        return redirect('farmer_orders')

    # Get only the items that belong to this farmer
    order_items = order.items.filter(product__seller=request.user)

    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'users/farmer_order_detail.html', context)