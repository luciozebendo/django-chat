from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import SignUpForm


def frontpage(request):
    return render(request, "core/frontpage.html")


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        # Django's UserCreationForm validates the username and that both passwords match.
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("rooms")
    else:
        form = SignUpForm()

    return render(request, "core/signup.html", {"form": form})
