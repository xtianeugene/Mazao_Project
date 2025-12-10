# orders/urls.py
from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('order/<uuid:order_id>/', views.order_detail, name='order_detail'),
    # Remove or fix the 'history/' URL if it exists
    # path('history/', views.order_history, name='order_history'),  # Remove or comment this
]