# payments/urls.py
from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # M-Pesa payment flow
    path('mpesa/', views.initiate_mpesa_payment, name='initiate_mpesa'),
    path('mpesa/process/', views.process_mpesa_payment, name='process_mpesa'),
    path('mpesa/processing/<uuid:payment_id>/', views.mpesa_payment_processing, name='mpesa_processing'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    path('check-status/<uuid:payment_id>/', views.check_payment_status, name='check_payment_status'),

    # Success and history
    path('success/', views.payment_success, name='payment_success'),
    path('history/', views.payment_history, name='history'),
    path('failed/<uuid:payment_id>/', views.payment_failed, name='payment_failed'),
    path('detail/<uuid:payment_id>/', views.payment_detail, name='payment_detail'),
    path('cancel/<uuid:payment_id>/', views.cancel_payment, name='cancel_payment'),
    path('retry/<uuid:payment_id>/', views.retry_payment, name='retry_payment'),

    # Other payment methods (if needed)
    # path('card/', views.card_payment, name='card_payment'),
    # path('bank/', views.bank_transfer, name='bank_transfer'),
]