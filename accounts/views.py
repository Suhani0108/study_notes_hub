from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import SignUpForm


def signup(request):
    # Logged-in users don't need to sign up again
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()   # creates the user with a hashed password
            login(request, user)  # log them in straight away
            messages.success(request, f'Welcome, {user.username}! Your account is ready.')
            return redirect('dashboard')
    else:
        form = SignUpForm()  # empty form for a GET request

    return render(request, 'registration/signup.html', {'form': form})
