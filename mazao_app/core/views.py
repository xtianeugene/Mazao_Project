from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.views.generic import TemplateView
# Create your views here.

class HomeView(TemplateView):
    template_name = 'core/home.html'

def about_view(request):
    return render(request, 'core/about.html')


def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = request.POST.get('email', '')  # Get email from form
            user.username = user.email  # Set username to email
            user.save()
            messages.success(request, f'Account created for {user.email}!')
            return redirect('login')
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {'form': form})