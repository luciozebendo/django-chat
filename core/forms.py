from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignUpForm(UserCreationForm):
    """Django's built-in sign-up form, limited to username and password."""

    class Meta:
        model = User
        fields = ["username", "password1", "password2"]
