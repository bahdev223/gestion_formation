from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from organisations.models import InvitationOrganisation, MembreOrganisation, Organisation
from subscriptions.models import Abonnement, PlanAbonnement


class OrganisationAccessManagementTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organisation = Organisation.objects.create(
            nom="Entreprise Access",
            slug="entreprise-access",
            email="contact@access.test",
            telephone="+22300000000",
            statut=Organisation.Statut.ACTIVE,
        )
        plan = PlanAbonnement.objects.create(
            code=PlanAbonnement.Code.PRO,
            nom="Business Access",
            prix_mensuel=Decimal("50000"),
            prix_annuel=Decimal("500000"),
            max_utilisateurs=10,
            max_participants=1000,
            max_formations_actives=50,
            max_stockage_mo=2048,
        )
        Abonnement.objects.create(
            organisation=cls.organisation,
            plan=plan,
            statut=Abonnement.Statut.ACTIF,
            cycle=Abonnement.Cycle.MENSUEL,
            date_debut=timezone.now(),
            date_fin=timezone.now() + timedelta(days=30),
            montant=plan.prix_mensuel,
        )
        cls.owner = get_user_model().objects.create_user(
            username="owner-access",
            email="owner@access.test",
            password="MotDePasseSolide123!",
            role="ADMIN",
        )
        cls.owner_member = MembreOrganisation.objects.create(
            organisation=cls.organisation,
            user=cls.owner,
            role=MembreOrganisation.Role.PROPRIETAIRE,
        )

    def tenant_reverse(self, name, *args):
        return reverse(
            f"organisations:{name}",
            args=[self.organisation.slug, *args],
        )

    def test_owner_can_create_invitation(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.tenant_reverse("member-invite"), {
            "email": "caissier@access.test",
            "role": MembreOrganisation.Role.CAISSIER,
            "permission__finance.view": "on",
            "permission__finance.collect": "on",
        })
        self.assertEqual(response.status_code, 200)
        invitation = InvitationOrganisation.objects.get(email="caissier@access.test")
        self.assertEqual(invitation.organisation, self.organisation)
        self.assertContains(response, str(invitation.token))

    def test_last_owner_cannot_be_demoted(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            self.tenant_reverse("member-edit", self.owner_member.pk),
            {"role": MembreOrganisation.Role.ADMIN, "is_active": "on"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "dernier proprietaire actif")
        self.owner_member.refresh_from_db()
        self.assertEqual(self.owner_member.role, MembreOrganisation.Role.PROPRIETAIRE)

    def test_cashier_cannot_disburse_even_with_global_admin_role(self):
        cashier = get_user_model().objects.create_user(
            username="cashier-access",
            password="MotDePasseSolide123!",
            role="ADMIN",
        )
        MembreOrganisation.objects.create(
            organisation=self.organisation,
            user=cashier,
            role=MembreOrganisation.Role.CAISSIER,
        )
        self.client.force_login(cashier)
        response = self.client.post(
            self.tenant_reverse("comptes:mouvement_decaisser"),
            {"compte_id": 999, "montant": "1000"},
        )
        self.assertEqual(response.status_code, 403)

    def test_reader_cannot_open_user_settings(self):
        reader = get_user_model().objects.create_user(
            username="reader-access",
            password="MotDePasseSolide123!",
        )
        MembreOrganisation.objects.create(
            organisation=self.organisation,
            user=reader,
            role=MembreOrganisation.Role.LECTURE,
        )
        self.client.force_login(reader)
        response = self.client.get(self.tenant_reverse("members"))
        self.assertEqual(response.status_code, 403)

    def test_invitation_creates_membership_in_correct_organisation(self):
        invitation = InvitationOrganisation.objects.create(
            organisation=self.organisation,
            email="new.user@access.test",
            role=MembreOrganisation.Role.SECRETAIRE,
            expire_le=timezone.now() + timedelta(days=7),
            invited_by=self.owner,
        )
        response = self.client.post(
            reverse("organisation-invitation-accept", args=[invitation.token]),
            {
                "first_name": "Awa",
                "last_name": "Traore",
                "matricule": "EMP-ACCESS-01",
                "password1": "MotDePasseSolide123!",
                "password2": "MotDePasseSolide123!",
            },
        )
        self.assertRedirects(
            response,
            f"/o/{self.organisation.slug}/dashboard/",
            fetch_redirect_response=False,
        )
        user = get_user_model().objects.get(username="EMP-ACCESS-01")
        member = MembreOrganisation.objects.get(user=user)
        self.assertEqual(member.organisation, self.organisation)
        self.assertEqual(member.role, MembreOrganisation.Role.SECRETAIRE)
        invitation.refresh_from_db()
        self.assertEqual(invitation.statut, InvitationOrganisation.Statut.ACCEPTEE)
