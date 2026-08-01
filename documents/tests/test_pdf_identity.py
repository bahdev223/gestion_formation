from unittest.mock import patch

from django.test import TestCase

from dashboard.models import ConfigurationOrganisation
from documents.services.pdf_service import render_pdf
from organisations.models import Organisation


class PdfOrganisationIdentityTest(TestCase):
    def test_pdf_uses_official_tenant_name(self):
        organisation = Organisation.objects.create(
            nom="Centre Horizon",
            slug="centre-horizon",
            email="contact@horizon.test",
            telephone="+22370000000",
        )
        ConfigurationOrganisation.objects.create(
            organisation=organisation,
            nom="Ancienne identite",
        )

        with patch("documents.services.pdf_service.render_to_string") as render:
            with patch("documents.services.pdf_service.HTML") as html:
                html.return_value.write_pdf.return_value = b"pdf"
                render.return_value = "<html></html>"
                payload = render_pdf(
                    "documents/pdf/receipt.html",
                    {"active_organisation": organisation},
                )

        self.assertEqual(payload, b"pdf")
        context = render.call_args.args[1]
        self.assertEqual(context["company_name"], "Centre Horizon")
