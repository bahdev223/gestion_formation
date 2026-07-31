from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import UpdateView

from organisations.utils import (
    get_user_default_organisation,
    require_request_organisation,
    tenant_reverse,
)

from .forms import ConfigurationOrganisationForm
from .models import ConfigurationOrganisation

try:
    from .services.dashboard_service import get_dashboard_statistics
except Exception:  # pragma: no cover - compatibility fallback for deploys
    from . import selectors
    get_dashboard_statistics = getattr(selectors, "get_dashboard_statistics", None)

if get_dashboard_statistics is None:  # pragma: no cover - defensive guard
    raise ImproperlyConfigured(
        "Le sélecteur dashboard n'expose pas get_dashboard_statistics."
    )


@login_required
def dashboard_home(request, **kwargs):
    if getattr(request, "organisation", None) is None:
        organisation = get_user_default_organisation(request.user)
        if organisation is not None:
            return redirect(f"/o/{organisation.slug}/dashboard/")

    organisation = require_request_organisation(request)
    stats = get_dashboard_statistics(
        {
            "request": request,
            "organisation": organisation,
        },
    )

    if "error" not in stats:
        # Compatibilité avec d'anciens composants attendants des variables simples.
        stats.setdefault("title", "Tableau de bord")
        stats.setdefault(
            "bread_crumbs",
            [
                "Tableau de bord",
                "Direction",
            ],
        )

    return render(request, "dashboard/index.html", stats)


class ConfigurationOrganisationView(
    LoginRequiredMixin, SuccessMessageMixin, UpdateView
):
    model = ConfigurationOrganisation
    form_class = ConfigurationOrganisationForm
    template_name = "dashboard/organisation_form.html"

    def get_success_url(self):
        return tenant_reverse(self.request, "dashboard:organisation-settings")

    success_message = "Les paramètres de l'entreprise ont été enregistrés."

    def get_object(self, queryset=None):
        organisation = require_request_organisation(self.request)
        qs = ConfigurationOrganisation.objects.filter(
            organisation=organisation
        ).order_by("pk")
        configuration = qs.first()
        if configuration is None:
            configuration = ConfigurationOrganisation.objects.create(
                organisation=organisation,
                nom=organisation.nom,
            )
        return configuration

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context["form"]
        context["identity_fields"] = [
            form["nom"],
            form["logo"],
            form["adresse"],
            form["telephone"],
            form["email"],
            form["site_web"],
            form["numero_fiscal"],
            form["devise"],
        ]
        context["document_fields"] = [
            form["prefixe_recu"],
            form["prefixe_attestation"],
            form["signature_nom"],
            form["signature_fonction"],
            form["signature_image"],
            form["cachet_image"],
        ]
        context["theme_fields"] = [
            form["couleur_sidebar"],
            form["couleur_header"],
            form["couleur_primaire"],
            form["couleur_secondaire"],
            form["couleur_accent"],
            form["couleur_fond"],
            form["couleur_surface"],
        ]
        context["theme_palettes"] = [
            {
                "code": "BALYS",
                "label": "BALY'S",
                "sidebar": "#0b2448",
                "header": "#ffffff",
                "primary": "#15519a",
                "secondary": "#102f5d",
                "accent": "#f28b16",
                "background": "#f4f6f9",
                "surface": "#ffffff",
            },
            {
                "code": "OCEAN",
                "label": "Ocean",
                "sidebar": "#083344",
                "header": "#f8fafc",
                "primary": "#0e7490",
                "secondary": "#155e75",
                "accent": "#f59e0b",
                "background": "#f1f5f9",
                "surface": "#ffffff",
            },
            {
                "code": "EMERALD",
                "label": "Emerald",
                "sidebar": "#064e3b",
                "header": "#ffffff",
                "primary": "#047857",
                "secondary": "#065f46",
                "accent": "#d97706",
                "background": "#f6f8f7",
                "surface": "#ffffff",
            },
            {
                "code": "BORDEAUX",
                "label": "Bordeaux",
                "sidebar": "#3f1222",
                "header": "#fffafa",
                "primary": "#8a1538",
                "secondary": "#5f1028",
                "accent": "#c98a2e",
                "background": "#f7f5f5",
                "surface": "#ffffff",
            },
        ]
        return context
