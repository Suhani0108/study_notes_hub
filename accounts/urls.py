from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    # Django's built-in login/logout views do the hard work for us
    path(
        'login/',
        auth_views.LoginView.as_view(
            authentication_form=LoginForm,
            redirect_authenticated_user=True,  # skip the form if already logged in
        ),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),  # POST only
]
