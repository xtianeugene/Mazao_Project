from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('history/', views.payment_history, name='payment_history'),
    path('detail/<uuid:payment_id>/', views.payment_detail, name='payment_detail'),
    path('wallet/', views.wallet_view, name='wallet'),
    path('wallet/deposit/', views.wallet_deposit, name='wallet_deposit'),
    path('wallet/withdraw/', views.wallet_withdraw, name='wallet_withdraw'),
    path('success/', views.payment_success, name='payment_success'),
    path('failed/<uuid:payment_id>/', views.payment_failed, name='payment_failed'),
    path('cancel/<uuid:payment_id>/', views.cancel_payment, name='cancel_payment'),
    path('retry/<uuid:payment_id>/', views.retry_payment, name='retry_payment'),
    path('transactions/', views.transaction_history, name='transaction_history'),
    path('admin/all/', views.admin_payments, name='admin_payments'),
]