import tempfile

from django.test import override_settings

from documents.models import Attestation, DocumentGenere
from documents.services.attestation_service import generate_attestation
from documents.services.generation_service import generate_document
from presences.tests.test_services import PresenceServiceTest as _PresenceServiceTest


class DocumentServiceTest(_PresenceServiceTest):
    def setUp(self):
        super().setUp()
        self.inscription.statut = self.inscription.Statut.TERMINE
        self.inscription.session.seuil_presence_attestation = 0
        self.inscription.session.paiement_requis_attestation = False
        self.inscription.session.save(
            update_fields=[
                "seuil_presence_attestation",
                "paiement_requis_attestation",
            ]
        )
        self.inscription.save(update_fields=["statut"])

    def test_generation_attestation_pdf(self):
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media):
                attestation = generate_attestation(
                    self.inscription, self.user
                )
                self.assertEqual(
                    attestation.statut, Attestation.Statut.GENEREE
                )
                self.assertTrue(attestation.fichier_pdf.name.endswith(".pdf"))
                with attestation.fichier_pdf.open("rb") as stream:
                    self.assertTrue(stream.read(4).startswith(b"%PDF"))

    def test_document_reference_est_reutilise(self):
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media):
                first = generate_document(
                    document_type=DocumentGenere.TypeDocument.LISTE_PARTICIPANTS,
                    reference=self.session.code,
                    template="documents/pdf/participant_list.html",
                    context={
                        "session": self.session,
                        "inscriptions": [self.inscription],
                    },
                    user=self.user,
                )
                second = generate_document(
                    document_type=DocumentGenere.TypeDocument.LISTE_PARTICIPANTS,
                    reference=self.session.code,
                    template="documents/pdf/participant_list.html",
                    context={
                        "session": self.session,
                        "inscriptions": [self.inscription],
                    },
                    user=self.user,
                )
                self.assertEqual(first.pk, second.pk)
                self.assertEqual(DocumentGenere.objects.count(), 1)
