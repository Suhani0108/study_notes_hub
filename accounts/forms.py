from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class BootstrapFormMixin:
    """Adds the right Bootstrap CSS class to every field."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'


class SignUpForm(BootstrapFormMixin, UserCreationForm):
    """Django's built-in sign-up form, plus a required email field."""

    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email')  # password fields come from UserCreationForm


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    """Django's built-in login form, styled with Bootstrap."""
