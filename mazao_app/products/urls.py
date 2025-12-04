# products/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Product listing
    path('', views.ProductListView.as_view(), name='product_list'),
    path('featured/', views.featured_products, name='featured_products'),
    path('category/<slug:slug>/', views.products_by_category, name='products_by_category'),

    # Product management
    path('add/', views.ProductCreateView.as_view(), name='add_product'),
    path('create/', views.ProductCreateView.as_view(), name='product_create'),
    path('my-products/', views.my_products, name='my_products'),
    path('farmer-products/', views.farmer_products, name='farmer_products'),
    path('edit/<slug:slug>/', views.ProductUpdateView.as_view(), name='edit_product'),
    path('delete/<slug:slug>/', views.ProductDeleteView.as_view(), name='delete_product'),

    # Product detail
    path('<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),

    # Reviews
    path('<slug:slug>/review/', views.add_review, name='add_review'),
    path('<slug:slug>/review/update/', views.update_review, name='update_review'),

    # Wishlist
    path('<slug:slug>/wishlist/toggle/', views.toggle_wishlist, name='toggle_wishlist'),
    path('wishlist/', views.wishlist_view, name='wishlist'),

    # Quick view (AJAX)
    path('<slug:slug>/quick-view/', views.product_quick_view, name='product_quick_view'),
]