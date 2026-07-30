from django.shortcuts import redirect
from django.urls import reverse


class MandatoryPasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and request.user.must_change_password
            and request.path
            not in {
                reverse("accounts:change-password"),
                reverse("accounts:logout"),
            }
            and not request.path.startswith(("/static/", "/media/"))
        ):
            return redirect("accounts:change-password")
        return self.get_response(request)
