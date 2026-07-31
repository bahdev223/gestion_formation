from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.shortcuts import redirect

from organisations.utils import get_user_default_organisation
from platform_admin.access import get_platform_role

from .forms import EmailOrMatriculeAuthenticationForm, StyledPasswordChangeForm


class UserLoginView(LoginView):
    authentication_form = EmailOrMatriculeAuthenticationForm
    template_name = "accounts/login.html"

    # Duree de la session quand « Se souvenir de moi » est coche.
    REMEMBER_ME_SECONDS = 60 * 60 * 24 * 30

    def form_valid(self, form):
        response = super().form_valid(form)
        # Sans cette case, la session expire a la fermeture du navigateur.
        if self.request.POST.get("remember_me"):
            self.request.session.set_expiry(self.REMEMBER_ME_SECONDS)
        else:
            self.request.session.set_expiry(0)
        return response

    def get_success_url(self):
        if self.request.user.must_change_password:
            return "/accounts/change-password/"
        # Une destination explicite (?next=) doit gagner sur la redirection par
        # role : sans cela, un utilisateur envoye vers /admin/ par
        # AdminPathSecurityMiddleware atterrissait sur son tableau de bord.
        # get_redirect_url() de LoginView rejette deja les URL externes.
        redirection_demandee = self.get_redirect_url()
        if redirection_demandee:
            return redirection_demandee
        if get_platform_role(self.request.user):
            return "/platform/"
        organisation = get_user_default_organisation(self.request.user)
        if organisation is not None:
            return f"/o/{organisation.slug}/dashboard/"
        return super().get_success_url()

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.must_change_password:
                return redirect("accounts:change-password")
            if get_platform_role(request.user):
                return redirect("/platform/")
            organisation = get_user_default_organisation(request.user)
            if organisation is not None:
                return redirect(f"/o/{organisation.slug}/dashboard/")
        return super().dispatch(request, *args, **kwargs)


class UserLogoutView(LogoutView):
    pass


class MandatoryPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = StyledPasswordChangeForm
    template_name = "accounts/change_password.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.user.must_change_password = False
        self.request.user.save(update_fields=["must_change_password", "updated_at"])
        messages.success(self.request, "Votre mot de passe personnel est maintenant actif.")
        return response

    def get_success_url(self):
        if get_platform_role(self.request.user):
            return "/platform/"
        organisation = get_user_default_organisation(self.request.user)
        if organisation is not None:
            return f"/o/{organisation.slug}/dashboard/"
        return "/"
