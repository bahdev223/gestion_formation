from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from organisations.models import Organisation
from participants.models import Participant


class TenantIntegrityCommandTest(TestCase):
    def test_audit_reussit_sans_donnee_orpheline(self):
        output = StringIO()

        call_command("audit_tenant_integrity", stdout=output)

        self.assertIn("aucune donnee orpheline", output.getvalue())

    def test_repare_une_base_historique_mono_entreprise(self):
        organisation = Organisation.objects.create(
            nom="Centre historique",
            slug="centre-historique",
            email="historique@example.test",
            telephone="+22370000000",
        )
        participant = Participant.objects.create(
            nom="Diallo",
            prenom="Aminata",
            telephone="+22370000001",
        )

        call_command("audit_tenant_integrity", "--fix-single-tenant")

        participant.refresh_from_db()
        self.assertEqual(participant.organisation, organisation)
