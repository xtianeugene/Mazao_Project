from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from .models import Product, Category, ProductReview, Wishlist
from .forms import ProductForm, ProductSearchForm, ProductReviewForm
from users.models import CustomUser
from django.db import models

# Product List View
@login_required
def my_products(request):
    # Get products owned by current user
    products = Product.objects.filter(seller=request.user)

    # Calculate statistics
    products_active_count = products.filter(status=Product.ProductStatus.ACTIVE).count()
    products_out_of_stock_count = products.filter(status=Product.ProductStatus.OUT_OF_STOCK).count()
    total_views = products.aggregate(total_views=models.Sum('views'))['total_views'] or 0

    context = {
        'products': products,
        'products_active_count': products_active_count,
        'products_out_of_stock_count': products_out_of_stock_count,
        'total_views': total_views,
        'title': 'My Products'
    }
    return render(request, 'products/my_products.html', context)

class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(status=Product.ProductStatus.ACTIVE)

        # Apply filters from search form
        form = ProductSearchForm(self.request.GET)
        if form.is_valid():
            query = form.cleaned_data.get('query')
            category = form.cleaned_data.get('category')
            min_price = form.cleaned_data.get('min_price')
            max_price = form.cleaned_data.get('max_price')
            location = form.cleaned_data.get('location')
            organic_only = form.cleaned_data.get('organic_only')
            fresh_only = form.cleaned_data.get('fresh_only')
            sort_by = form.cleaned_data.get('sort_by')

            # Search query
            if query:
                queryset = queryset.filter(
                    Q(name__icontains=query) |
                    Q(description__icontains=query) |
                    Q(farmer__first_name__icontains=query) |
                    Q(farmer__last_name__icontains=query)
                )

            # Category filter
            if category:
                queryset = queryset.filter(category=category)

            # Price range filter
            if min_price:
                queryset = queryset.filter(price__gte=min_price)
            if max_price:
                queryset = queryset.filter(price__lte=max_price)

            # Location filter
            if location:
                queryset = queryset.filter(
                    Q(location__icontains=location) |
                    Q(county__icontains=location)
                )

            # Additional filters
            if organic_only:
                queryset = queryset.filter(is_organic=True)
            if fresh_only:
                queryset = queryset.filter(is_fresh=True)

            # Sorting
            if sort_by == 'price_asc':
                queryset = queryset.order_by('price')
            elif sort_by == 'price_desc':
                queryset = queryset.order_by('-price')
            elif sort_by == 'popular':
                queryset = queryset.order_by('-views')
            else:  # newest
                queryset = queryset.order_by('-created_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.annotate(product_count=Count('products')).order_by('name')
        context['search_form'] = ProductSearchForm(self.request.GET)

        # Get featured products
        context['featured_products'] = Product.objects.filter(
            status=Product.ProductStatus.ACTIVE,
            featured=True
        )[:6]

        return context


# Product Detail View
class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'

    def get_object(self):
        obj = super().get_object()
        # Increment view count
        obj.increment_views()
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        # Get related products (same category)
        context['related_products'] = Product.objects.filter(
            category=product.category,
            status=Product.ProductStatus.ACTIVE
        ).exclude(id=product.id)[:4]

        # Get product reviews with stats
        reviews = product.reviews.all()
        context['reviews'] = reviews[:5]  # Show only 5 latest reviews

        # Calculate average rating
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        context['average_rating'] = round(avg_rating, 1) if avg_rating else 0
        context['total_reviews'] = reviews.count()

        # Rating distribution
        rating_counts = {i: 0 for i in range(5, 0, -1)}
        for review in reviews:
            rating_counts[review.rating] = rating_counts.get(review.rating, 0) + 1
        context['rating_counts'] = rating_counts

        # Check if user has reviewed this product
        if self.request.user.is_authenticated:
            context['user_review'] = reviews.filter(user=self.request.user).first()

        # Check if product is in user's wishlist
        if self.request.user.is_authenticated:
            context['in_wishlist'] = Wishlist.objects.filter(
                user=self.request.user,
                product=product
            ).exists()

        # Review form
        if self.request.user.is_authenticated and not context.get('user_review'):
            context['review_form'] = ProductReviewForm()

        return context


# Product Create View (Farmer only)
class ProductCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'

    def test_func(self):
        return self.request.user.is_farmer

    def handle_no_permission(self):
        messages.error(self.request, "Only farmers can add products.")
        return redirect('home')

    def form_valid(self, form):
        form.instance.farmer = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f"Product '{form.instance.name}' created successfully!")
        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Product'
        return context


# Product Update View (Farmer only, and only their own products)
class ProductUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'

    def test_func(self):
        product = self.get_object()
        return self.request.user.is_farmer and product.farmer == self.request.user

    def handle_no_permission(self):
        messages.error(self.request, "You can only edit your own products.")
        return redirect('home')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Product '{form.instance.name}' updated successfully!")
        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Product'
        return context


# Product Delete View
class ProductDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Product
    template_name = 'products/product_confirm_delete.html'
    success_url = reverse_lazy('farmer_products')

    def test_func(self):
        product = self.get_object()
        return self.request.user.is_farmer and product.farmer == self.request.user

    def delete(self, request, *args, **kwargs):
        product = self.get_object()
        messages.success(request, f"Product '{product.name}' deleted successfully!")
        return super().delete(request, *args, **kwargs)


# Farmer's Product List
@login_required
def farmer_products(request):
    if not request.user.is_farmer:
        messages.error(request, "Only farmers can access this page.")
        return redirect('home')

    products = Product.objects.filter(farmer=request.user).order_by('-created_at')

    # Get statistics
    total_products = products.count()
    active_products = products.filter(status=Product.ProductStatus.ACTIVE).count()
    out_of_stock = products.filter(status=Product.ProductStatus.OUT_OF_STOCK).count()
    total_views = products.aggregate(total_views=models.Sum('views'))['total_views'] or 0

    context = {
        'products': products,
        'total_products': total_products,
        'active_products': active_products,
        'out_of_stock': out_of_stock,
        'total_views': total_views,
    }

    return render(request, 'products/farmer_products.html', context)


# Add Product Review
@login_required
def add_review(request, slug):
    product = get_object_or_404(Product, slug=slug)

    # Check if user already reviewed this product
    existing_review = ProductReview.objects.filter(product=product, user=request.user).first()
    if existing_review:
        messages.warning(request, "You have already reviewed this product.")
        return redirect('product_detail', slug=slug)

    if request.method == 'POST':
        form = ProductReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, "Thank you for your review!")
            return redirect('product_detail', slug=slug)
    else:
        form = ProductReviewForm()

    return render(request, 'products/add_review.html', {
        'form': form,
        'product': product,
    })


# Update Product Review
@login_required
def update_review(request, slug):
    product = get_object_or_404(Product, slug=slug)
    review = get_object_or_404(ProductReview, product=product, user=request.user)

    if request.method == 'POST':
        form = ProductReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, "Your review has been updated!")
            return redirect('product_detail', slug=slug)
    else:
        form = ProductReviewForm(instance=review)

    return render(request, 'products/update_review.html', {
        'form': form,
        'product': product,
        'review': review,
    })


# Toggle Wishlist
@login_required
def toggle_wishlist(request, slug):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        product = get_object_or_404(Product, slug=slug)
        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user,
            product=product
        )

        if not created:
            # Item already in wishlist, remove it
            wishlist_item.delete()
            in_wishlist = False
            message = "Product removed from wishlist"
        else:
            in_wishlist = True
            message = "Product added to wishlist"

        return JsonResponse({
            'success': True,
            'in_wishlist': in_wishlist,
            'message': message
        })

    return JsonResponse({'success': False, 'error': 'Invalid request'})


# Wishlist View
@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')

    context = {
        'wishlist_items': wishlist_items,
    }

    return render(request, 'products/wishlist.html', context)


# Products by Category
def products_by_category(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(
        category=category,
        status=Product.ProductStatus.ACTIVE
    ).order_by('-created_at')

    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'category': category,
        'products': page_obj,
        'page_obj': page_obj,
    }

    return render(request, 'products/products_by_category.html', context)


# Featured Products
def featured_products(request):
    products = Product.objects.filter(
        status=Product.ProductStatus.ACTIVE,
        featured=True
    ).order_by('-created_at')

    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'title': 'Featured Products',
    }

    return render(request, 'products/featured_products.html', context)


# Product Quick View (for AJAX requests)
def product_quick_view(request, slug):
    product = get_object_or_404(Product, slug=slug)

    context = {
        'product': product,
    }

    return render(request, 'products/partials/product_quick_view.html', context)