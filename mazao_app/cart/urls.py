# cart/urls.py
from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('add/', views.add_to_cart, name='add'),
    path('add-item/', views.add_to_cart, name='add_item'),
    path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('', views.view_cart, name='view_cart'),
    path('count/', views.cart_item_count, name='cart_item_count'),
    path('checkout/', views.checkout, name='checkout'),
    path('process-payment/', views.process_payment, name='process_payment'),
    path('mpesa-payment/', views.mpesa_payment, name='mpesa_payment'),
    path('payment-status/<int:transaction_id>/', views.payment_status, name='payment_status'),
    path('cash-on-delivery/', views.cash_on_delivery, name='cash_on_delivery'),
    path('bank-transfer/', views.bank_transfer, name='bank_transfer'),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('mpesa-callback/', views.mpesa_callback, name='mpesa_callback'),
    path('payment-processing/', views.payment_processing, name='payment_processing'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-failed/', views.payment_failed, name='payment_failed'),

]