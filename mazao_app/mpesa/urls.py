from django.urls import path
from . import views

app_name = 'mpesa'

urlpatterns = [
    path('', views.index, name='index'),
    path('pay/', views.initiate_payment, name='initiate_payment'),
    path('payment-status/<str:checkout_request_id>/', views.payment_status, name='payment_status'),
    path('check-status/<str:checkout_request_id>/', views.check_status, name='check_status'),
    path('callback/', views.stk_push_callback, name='mpesa_callback'),
    path('history/', views.payment_history, name='payment_history'),
    path('test/', views.test_payment, name='test_payment'),
    path('initiate_payment/', views.initiate_payment, name='initiate_payment_alias'),
]