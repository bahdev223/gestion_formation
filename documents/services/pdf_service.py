from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from weasyprint import HTML


def render_pdf(template_name, context):
    from dashboard.models import ConfigurationOrganisation

    payload = dict(context)
    payload.setdefault(
        "organisation", ConfigurationOrganisation.objects.first()
    )
    html = render_to_string(template_name, payload)
    return HTML(
        string=html,
        base_url=str(settings.BASE_DIR),
    ).write_pdf()


def replace_file(field, filename, payload):
    if field:
        field.delete(save=False)
    field.save(filename, ContentFile(payload), save=False)
