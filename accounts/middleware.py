from django.shortcuts import redirect
from django.urls import reverse


class ActiveUserRequiredMiddleware:
    """Redirects authenticated but inactive users to a warning page."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_active:
            inactive_url = reverse("accounts:inactive")
            allowed = {inactive_url}
            if request.path not in allowed:
                return redirect("accounts:inactive")
        return self.get_response(request)
