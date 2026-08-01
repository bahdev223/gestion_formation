from django.db import transaction

from documents.models import DocumentGenere
from documents.services.pdf_service import render_pdf, replace_file


@transaction.atomic
def generate_document(*, document_type, reference, template, context, user, organisation=None):
    document, _created = DocumentGenere.objects.get_or_create(
        type_document=document_type,
        reference=reference,
        defaults={"genere_par": user, "organisation": organisation},
    )
    if organisation is not None:
        document.organisation = organisation
    document.genere_par = user
    document.metadata = {
        "template": template,
        "reference": reference,
    }
    render_context = {**context, "active_organisation": organisation}
    payload = render_pdf(template, render_context)
    filename = f"{document_type.lower()}-{reference}.pdf".replace("/", "-")
    replace_file(document.fichier, filename, payload)
    document.save()
    return document
