from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
urlpatterns = [
    # Authentication URLs
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('register/', views.register_view, name='register'),

    # Profile URLs
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update_view, name='profile_update'),
    path('profile/farmer/complete/', views.complete_farmer_profile, name='complete_farmer_profile'),
    path('profile/buyer/complete/', views.complete_buyer_profile, name='complete_buyer_profile'),

    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),

]