from django.urls import path
from . import views

app_name = 'products'  # Namespace is important!

urlpatterns = [
    path('', views.ProductListView.as_view(), name='product_list'),
    path('my-products/', views.my_products, name='my_products'),
    path('add/', views.ProductCreateView.as_view(), name='add_product'),  # This should be here
    path('farmer-products/', views.farmer_products, name='farmer_products'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('featured/', views.featured_products, name='featured_products'),
    path('category/<slug:slug>/', views.products_by_category, name='products_by_category'),
    path('<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('<slug:slug>/edit/', views.ProductUpdateView.as_view(), name='edit_product'),
    path('<slug:slug>/delete/', views.ProductDeleteView.as_view(), name='delete_product'),
    path('<slug:slug>/add-review/', views.add_review, name='add_review'),
    path('<slug:slug>/update-review/', views.update_review, name='update_review'),
    path('<slug:slug>/toggle-wishlist/', views.toggle_wishlist, name='toggle_wishlist'),
    path('<slug:slug>/quick-view/', views.product_quick_view, name='product_quick_view'),
]