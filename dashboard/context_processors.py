from django.db import DatabaseError

from organisations.utils import get_request_organisation

from .models import ConfigurationOrganisation

DEFAULT_THEME = {
    "sidebar": "#0b2448",
    "header": "#ffffff",
    "primary": "#15519a",
    "secondary": "#102f5d",
    "accent": "#f28b16",
    "background": "#f4f6f9",
    "surface": "#ffffff",
}


def _strip_or_empty(value):
    if value is None:
        return ""
    return str(value).strip()


def _resolve_company_name(configuration, active_organisation):
    config_name = _strip_or_empty(getattr(configuration, "nom", ""))
    if config_name and config_name.upper() not in {"BALY'S GROUP", "BALY’S GROUP"}:
        return config_name

    active_name = _strip_or_empty(getattr(active_organisation, "nom", ""))
    if active_name:
        return active_name

    return "Votre entreprise"


def _resolve_company_logo(configuration, active_organisation):
    def _is_existing(logo_field):
        from django.core.files.storage import default_storage

        if not logo_field:
            return False
        name = getattr(logo_field, "name", None)
        if not name:
            return False
        storage = getattr(logo_field, "storage", None) or default_storage
        return storage.exists(name)

    config_logo = getattr(configuration, "logo", None)
    if _is_existing(config_logo):
        return config_logo
    org_logo = getattr(active_organisation, "logo", None)
    if _is_existing(org_logo):
        return org_logo
    return None


def organisation(request):
    active_organisation = get_request_organisation(request)
    try:
        qs = ConfigurationOrganisation.objects.order_by("pk")
        if active_organisation:
            qs = qs.filter(organisation=active_organisation)
        configuration = qs.first()
    except DatabaseError:
        configuration = None

    organisation_name = _resolve_company_name(configuration, active_organisation)
    organisation_logo = _resolve_company_logo(configuration, active_organisation)
    theme = DEFAULT_THEME.copy()
    if configuration:
        theme.update(
            {
                "sidebar": configuration.couleur_sidebar,
                "header": configuration.couleur_header,
                "primary": configuration.couleur_primaire,
                "secondary": configuration.couleur_secondaire,
                "accent": configuration.couleur_accent,
                "background": configuration.couleur_fond,
                "surface": configuration.couleur_surface,
            }
        )
    return {
        "organisation": configuration,
        "organisation_theme": theme,
        "company_name": organisation_name,
        "company_logo": organisation_logo,
    }
