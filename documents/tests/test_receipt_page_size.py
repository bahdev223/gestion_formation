from types import SimpleNamespace

from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from weasyprint import HTML


class ReceiptPageSizeTest(SimpleTestCase):
    def test_receipt_is_one_physical_a5_page(self):
        participant = SimpleNamespace(nom_complet="Awa Traore")
        formation = SimpleNamespace(nom="Gestion de projet")
        session = SimpleNamespace(formation=formation, titre="Session aout")
        inscription = SimpleNamespace(
            participant=participant,
            session=session,
            numero="INS-001",
        )
        paiement = SimpleNamespace(
            numero_recu="REC-001",
            date_paiement=None,
            inscription=inscription,
            compte=SimpleNamespace(nom="Caisse principale"),
            get_mode_paiement_display=lambda: "Especes",
            reference_transaction="",
            montant=15000,
        )
        organisation = SimpleNamespace(
            adresse="Bamako",
            telephone="+22370000000",
            email="contact@example.test",
            signature_nom="La Direction",
            signature_fonction="",
        )
        html = render_to_string(
            "documents/pdf/receipt.html",
            {
                "paiement": paiement,
                "organisation": organisation,
                "company_name": "Centre Horizon",
                "company_logo_url": "",
                "payment_currency": "XOF",
            },
        )

        document = HTML(string=html, base_url=str(settings.BASE_DIR)).render()

        millimetre_in_css_pixels = 96 / 25.4
        self.assertEqual(len(document.pages), 1)
        self.assertAlmostEqual(
            document.pages[0].width,
            148 * millimetre_in_css_pixels,
            places=2,
        )
        self.assertAlmostEqual(
            document.pages[0].height,
            210 * millimetre_in_css_pixels,
            places=2,
        )
