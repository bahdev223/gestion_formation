from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect

from organisations.utils import get_user_default_organisation
from platform_admin.access import get_platform_role

from .forms import EmailOrMatriculeAuthenticationForm


class UserLoginView(LoginView):
    authentication_form = EmailOrMatriculeAuthenticationForm
    template_name = "accounts/login.html"

    def get_success_url(self):
        if get_platform_role(self.request.user):
            return "/platform/"
        organisation = get_user_default_organisation(self.request.user)
        if organisation is not None:
            return f"/o/{organisation.slug}/dashboard/"
        return super().get_success_url()

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if get_platform_role(request.user):
                return redirect("/platform/")
            organisation = get_user_default_organisation(request.user)
            if organisation is not None:
                return redirect(f"/o/{organisation.slug}/dashboard/")
        return super().dispatch(request, *args, **kwargs)


class UserLogoutView(LogoutView):
    pass
