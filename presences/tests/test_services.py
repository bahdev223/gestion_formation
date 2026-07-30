from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from formations.models import CategorieFormation, Formation, Seance, SessionFormation
from inscriptions.models import Inscription
from organisations.models import MembreOrganisation, Organisation
from participants.models import Participant
from presences.models import Presence
from presences.services.presence_service import (
    calculate_attendance_rate,
    save_presence,
)


class PresenceServiceTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="responsable", password="test1234"
        )
        self.organisation = Organisation.objects.create(
            nom="Centre Test",
            slug="centre-test",
            email="contact@centre-test.test",
            telephone="+22370000002",
        )
        MembreOrganisation.objects.create(
            organisation=self.organisation,
            user=self.user,
            role=MembreOrganisation.Role.PROPRIETAIRE,
        )
        categorie = CategorieFormation.objects.create(
            organisation=self.organisation,
            nom="Gestion",
        )
        formation = Formation.objects.create(
            organisation=self.organisation,
            nom="Gestion de projet",
            categorie=categorie,
            duree=20,
            prix_standard=Decimal("100000"),
            statut=Formation.Statut.ACTIVE,
        )
        self.session = SessionFormation.objects.create(
            organisation=self.organisation,
            formation=formation,
            titre="Session test",
            formateur=self.user,
            date_debut=date.today(),
            date_fin=date.today(),
            lieu="Bamako",
            prix_applique=Decimal("100000"),
        )
        self.seance = Seance.objects.create(
            organisation=self.organisation,
            session=self.session,
            titre="Séance 1",
            date=date.today(),
            heure_debut=time(9),
            heure_fin=time(12),
        )
        participant = Participant.objects.create(
            organisation=self.organisation,
            nom="Diallo", prenom="Awa", telephone="70000000"
        )
        self.inscription = Inscription.objects.create(
            organisation=self.organisation,
            participant=participant,
            session=self.session,
            prix_initial=Decimal("100000"),
            montant_final=Decimal("100000"),
            statut=Inscription.Statut.CONFIRME,
            cree_par=self.user,
        )

    def test_enregistrement_et_taux_presence(self):
        save_presence(
            self.seance,
            self.inscription,
            Presence.Statut.PRESENT,
            self.user,
        )
        self.assertEqual(calculate_attendance_rate(self.inscription), 100)

    def test_refuse_inscription_autre_session(self):
        other = SessionFormation.objects.create(
            organisation=self.organisation,
            formation=self.session.formation,
            titre="Autre session",
            formateur=self.user,
            date_debut=date.today(),
            date_fin=date.today(),
            lieu="Bamako",
            prix_applique=Decimal("100000"),
        )
        self.inscription.session = other
        self.inscription.save(update_fields=["session"])
        with self.assertRaises(ValidationError):
            save_presence(
                self.seance,
                self.inscription,
                Presence.Statut.PRESENT,
                self.user,
            )
