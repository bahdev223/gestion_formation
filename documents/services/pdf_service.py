from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from weasyprint import HTML


def render_pdf(template_name, context):
    from dashboard.models import ConfigurationOrganisation

    payload = dict(context)
    active_organisation = payload.get("active_organisation")
    configuration = None
    if active_organisation is not None:
        configuration = (
            ConfigurationOrganisation.objects.filter(
                organisation=active_organisation
            )
            .order_by("pk")
            .first()
        )
    if configuration is None:
        configuration = ConfigurationOrganisation.objects.order_by("pk").first()

    profile = configuration or active_organisation
    payload["organisation"] = profile
    payload["company_name"] = (
        getattr(active_organisation, "nom", "")
        or getattr(profile, "nom", "")
        or "Entreprise"
    )
    payload["payment_currency"] = (
        getattr(profile, "devise", "")
        or getattr(active_organisation, "devise", "")
        or "Devise"
    )
    payload["company_logo_url"] = _resolve_logo_url(configuration, active_organisation)
    html = render_to_string(template_name, payload)
    return HTML(
        string=html,
        base_url=str(settings.BASE_DIR),
    ).write_pdf()


def _resolve_logo_url(configuration, active_organisation):
    for source in (configuration, active_organisation):
        logo = getattr(source, "logo", None)
        if not logo or not getattr(logo, "name", None):
            continue
        try:
            if hasattr(logo, "path"):
                from pathlib import Path

                return Path(logo.path).as_uri()
        except (NotImplementedError, ValueError):
            pass
        try:
            return logo.url
        except ValueError:
            continue
    return ""


def replace_file(field, filename, payload):
    if field:
        field.delete(save=False)
    field.save(filename, ContentFile(payload), save=False)
