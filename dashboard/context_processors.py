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


def organisation(request):
    active_organisation = get_request_organisation(request)
    try:
        qs = ConfigurationOrganisation.objects.order_by("pk")
        if active_organisation:
            qs = qs.filter(organisation=active_organisation)
        configuration = qs.first()
    except DatabaseError:
        configuration = None
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
    return {"organisation": configuration, "organisation_theme": theme}
