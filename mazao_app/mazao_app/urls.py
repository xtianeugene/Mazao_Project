"""
URL configuration for mazao_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import HomeView, register_view, about_view
from payments import views as payment_views

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('about/', about_view, name='about'),
    path('products/', include('products.urls')),
    path('cart/', include('cart.urls', namespace='cart')),
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('payments/', include('payments.urls')),
    path('orders/', include('orders.urls')),
    path('mpesa-payment/', payment_views.initiate_mpesa_payment, name='mpesa_payment'),

# Custom Authentication URLs
    path('users/login/', auth_views.LoginView.as_view(
        template_name='users/login.html',
        redirect_authenticated_user=True  # Redirect if already logged in
    ), name='login'),
    path('users/register/', register_view, name='register'),
    # Password Reset URLs
    path('users/password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='users/password_reset.html',
             email_template_name='users/password_reset_email.html',
             subject_template_name='users/password_reset_subject.txt',
             success_url='/users/password-reset/done/'
         ),
         name='password_reset'),

    path('users/password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='users/password_reset_done.html'
         ),
         name='password_reset_done'),

    path('users/password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='users/password_reset_confirm.html',
             success_url='/users/password-reset/complete/'
         ),
         name='password_reset_confirm'),

    path('users/password-reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='users/password_reset_complete.html'
         ),
         name='password_reset_complete'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)