from django.shortcuts import render
from django.views.generic import TemplateView
# Create your views here.
class HomeView(TemplateView):
    template_name = 'core/home.html'

def about_view(request):
    return render(request, 'core/about.html')