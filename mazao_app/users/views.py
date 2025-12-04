from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView
from django.contrib.auth.views import LoginView as AuthLoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import CustomUser, Profile, UserType
from .forms import (
    CustomUserCreationForm, FarmerRegistrationForm,
    BuyerRegistrationForm, ProfileUpdateForm, LoginForm
)
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
    context = {}

    if request.user.is_farmer:
        # Farmer dashboard context
        context['dashboard_type'] = 'farmer'
        context['title'] = 'Farmer Dashboard'
        # Add farmer-specific data later

    elif request.user.is_buyer:
        # Buyer dashboard context
        context['dashboard_type'] = 'buyer'
        context['title'] = 'Buyer Dashboard'
        # Add buyer-specific data later

    return render(request, 'users/dashboard.html', context)