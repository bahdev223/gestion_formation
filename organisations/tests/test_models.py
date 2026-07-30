from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from organisations.models import MembreOrganisation, Organisation


class OrganisationModelTest(TestCase):
    def test_slug_et_date_essai_sont_generes(self):
        organisation = Organisation.objects.create(
            nom="Centre Alpha",
            email="contact@alpha.test",
            telephone="+22300000000",
        )

        self.assertEqual(organisation.slug, "centre-alpha")
        self.assertIsNotNone(organisation.date_fin_essai)
        self.assertTrue(organisation.is_trial_active)

    def test_membre_unique_par_organisation(self):
        organisation = Organisation.objects.create(
            nom="Centre Alpha",
            email="contact@alpha.test",
            telephone="+22300000000",
        )
        user = get_user_model().objects.create_user(username="owner")
        MembreOrganisation.objects.create(
            organisation=organisation,
            user=user,
            role=MembreOrganisation.Role.PROPRIETAIRE,
        )

        with self.assertRaises(IntegrityError):
            MembreOrganisation.objects.create(
                organisation=organisation,
                user=user,
                role=MembreOrganisation.Role.ADMIN,
            )
