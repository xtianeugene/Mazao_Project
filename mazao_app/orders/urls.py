# orders/urls.py
from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('history/', views.order_history, name='order_history'),
    path('', views.order_list, name='order_list'),
    path('my-orders/', views.order_list, name='my_orders'),
    path('list/', views.order_list, name='list'),
]
