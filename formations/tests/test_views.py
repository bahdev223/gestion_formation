"""Tests for formations views."""

from datetime import date, time
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from formations.models import CategorieFormation, Formation, Seance, SessionFormation
from inscriptions.models import Inscription
from organisations.models import Organisation
from participants.models import Participant


class FormationCoverViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            username="formation-cover-admin",
            email="formation-cover@example.test",
            password="test1234",
        )
        cls.organisation = Organisation.objects.create(
            nom="Centre Couverture",
            slug="centre-couverture",
            email="contact@couverture.test",
            telephone="+22370000005",
        )
        from core.testing import souscrire_plan_complet

        souscrire_plan_complet(cls.organisation)
        cls.categorie = CategorieFormation.objects.create(
            organisation=cls.organisation,
            nom="Management couverture",
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_creation_enregistre_et_affiche_la_couverture(self):
        image_buffer = BytesIO()
        Image.new("RGB", (320, 180), color="#15519a").save(
            image_buffer,
            format="PNG",
        )
        upload = SimpleUploadedFile(
            "management.png",
            image_buffer.getvalue(),
            content_type="image/png",
        )
        create_url = (
            "/o/centre-couverture/formations/create/"
        )

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    create_url,
                    {
                        "nom": "Management opérationnel",
                        "categorie": self.categorie.pk,
                        "nouvelle_categorie": "",
                        "description": "Formation test",
                        "objectifs": "",
                        "programme": "",
                        "duree": 2,
                        "unite_duree": Formation.UniteDuree.JOURS,
                        "prix_standard": 150000,
                        "image": upload,
                        "statut": Formation.Statut.ACTIVE,
                    },
                )

                self.assertRedirects(
                    response,
                    "/o/centre-couverture/formations/",
                    fetch_redirect_response=False,
                )
                formation = Formation.objects.get(
                    nom="Management opérationnel"
                )
                self.assertTrue(formation.image.name.endswith(".png"))

                list_response = self.client.get(
                    "/o/centre-couverture/formations/"
                )
                self.assertContains(list_response, formation.image.url)

    def test_catalogue_utilise_une_couverture_par_defaut(self):
        Formation.objects.create(
            organisation=self.organisation,
            nom="Formation sans image",
            categorie=self.categorie,
            duree=4,
            prix_standard=50000,
        )

        response = self.client.get("/o/centre-couverture/formations/")

        self.assertContains(
            response,
            "/static/images/formation-cover-default.svg",
        )


class FormationCrudViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            username="formation-crud-admin",
            email="formation-crud@example.test",
            password="test1234",
        )
        cls.organisation = Organisation.objects.create(
            nom="Centre CRUD",
            slug="centre-crud",
            email="contact@crud.test",
            telephone="+22370000006",
        )
        from core.testing import souscrire_plan_complet

        souscrire_plan_complet(cls.organisation)
        cls.categorie = CategorieFormation.objects.create(
            organisation=cls.organisation,
            nom="Management CRUD",
        )
        cls.formation = Formation.objects.create(
            organisation=cls.organisation,
            nom="Gestion opérationnelle",
            categorie=cls.categorie,
            duree=5,
            prix_standard=100000,
            statut=Formation.Statut.ACTIVE,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_update_formation_via_form(self):
        url = f"/o/centre-crud/formations/{self.formation.pk}/modifier/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            url,
            {
                "nom": "Gestion opérationnelle avancée",
                "categorie": self.categorie.pk,
                "nouvelle_categorie": "",
                "description": "Mise Ã  jour test",
                "objectifs": "",
                "programme": "",
                "duree": 6,
                "unite_duree": Formation.UniteDuree.JOURS,
                "prix_standard": 120000,
                "statut": Formation.Statut.ACTIVE,
            },
        )
        self.assertRedirects(
            response,
            "/o/centre-crud/formations/",
            fetch_redirect_response=False,
        )
        self.formation.refresh_from_db()
        self.assertEqual(self.formation.nom, "Gestion opérationnelle avancée")
        self.assertEqual(self.formation.duree, 6)

    def test_delete_formation(self):
        formation_to_delete = Formation.objects.create(
            organisation=self.organisation,
            nom="A supprimer",
            categorie=self.categorie,
            duree=2,
            prix_standard=50000,
            statut=Formation.Statut.ACTIVE,
        )
        url = f"/o/centre-crud/formations/{formation_to_delete.pk}/supprimer/"
        response = self.client.post(url)
        self.assertRedirects(
            response,
            "/o/centre-crud/formations/",
            fetch_redirect_response=False,
        )
        self.assertFalse(Formation.objects.filter(pk=formation_to_delete.pk).exists())


class SessionSeanceCrudViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            username="session-crud-admin",
            email="session-crud@example.test",
            password="test1234",
        )
        cls.organisation = Organisation.objects.create(
            nom="Centre Sessions CRUD",
            slug="centre-sessions-crud",
            email="contact@sessions-crud.test",
            telephone="+22370000007",
        )
        from core.testing import souscrire_plan_complet

        souscrire_plan_complet(cls.organisation)
        cls.categorie = CategorieFormation.objects.create(
            organisation=cls.organisation,
            nom="Bureautique CRUD",
        )
        cls.formation = Formation.objects.create(
            organisation=cls.organisation,
            nom="Bureautique",
            categorie=cls.categorie,
            duree=5,
            prix_standard=100000,
            statut=Formation.Statut.ACTIVE,
        )
        cls.session = SessionFormation.objects.create(
            organisation=cls.organisation,
            formation=cls.formation,
            titre="Session initiale",
            formateur=cls.user,
            date_debut=date(2026, 8, 10),
            date_fin=date(2026, 8, 15),
            heure_debut=time(9, 0),
            heure_fin=time(12, 0),
            lieu="Salle A",
            capacite_max=20,
            prix_applique=100000,
            statut=SessionFormation.Statut.PLANIFIEE,
        )
        cls.seance = Seance.objects.create(
            organisation=cls.organisation,
            session=cls.session,
            titre="Introduction",
            date=date(2026, 8, 10),
            heure_debut=time(9, 0),
            heure_fin=time(12, 0),
            lieu="Salle A",
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_update_session_via_modal_form(self):
        url = f"/o/centre-sessions-crud/formations/sessions/{self.session.pk}/modifier/"
        response = self.client.get(url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            url,
            {
                "formation": self.formation.pk,
                "titre": "Session avancée",
                "formateur": self.user.pk,
                "date_debut": "2026-08-11",
                "date_fin": "2026-08-16",
                "heure_debut": "08:30",
                "heure_fin": "11:30",
                "lieu": "Salle B",
                "capacite_max": 25,
                "prix_applique": 120000,
                "seuil_presence_attestation": 75,
                "paiement_requis_attestation": "on",
                "notes": "",
                "statut": SessionFormation.Statut.INSCRIPTIONS_OUVERTES,
            },
        )

        self.assertRedirects(
            response,
            "/o/centre-sessions-crud/formations/sessions/",
            fetch_redirect_response=False,
        )
        self.session.refresh_from_db()
        self.assertEqual(self.session.titre, "Session avancée")
        self.assertEqual(self.session.lieu, "Salle B")

    def test_delete_session_without_inscriptions(self):
        session = SessionFormation.objects.create(
            organisation=self.organisation,
            formation=self.formation,
            titre="Session à supprimer",
            formateur=self.user,
            date_debut=date(2026, 9, 1),
            date_fin=date(2026, 9, 3),
            lieu="Salle C",
            capacite_max=10,
            prix_applique=50000,
        )
        response = self.client.post(
            f"/o/centre-sessions-crud/formations/sessions/{session.pk}/supprimer/"
        )

        self.assertRedirects(
            response,
            "/o/centre-sessions-crud/formations/sessions/",
            fetch_redirect_response=False,
        )
        self.assertFalse(SessionFormation.objects.filter(pk=session.pk).exists())

    def test_delete_session_with_inscriptions_is_refused(self):
        participant = Participant.objects.create(
            organisation=self.organisation,
            prenom="Aminata",
            nom="Diallo",
            telephone="+22370000008",
        )
        Inscription.objects.create(
            organisation=self.organisation,
            participant=participant,
            session=self.session,
            prix_initial=100000,
            montant_final=100000,
            cree_par=self.user,
        )

        response = self.client.post(
            f"/o/centre-sessions-crud/formations/sessions/{self.session.pk}/supprimer/"
        )

        self.assertRedirects(
            response,
            f"/o/centre-sessions-crud/formations/sessions/{self.session.pk}/",
            fetch_redirect_response=False,
        )
        self.assertTrue(SessionFormation.objects.filter(pk=self.session.pk).exists())

    def test_update_seance_via_modal_form(self):
        url = f"/o/centre-sessions-crud/formations/seances/{self.seance.pk}/modifier/"
        response = self.client.get(url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            url,
            {
                "session": self.session.pk,
                "titre": "Introduction avancée",
                "date": "2026-08-11",
                "heure_debut": "10:00",
                "heure_fin": "12:00",
                "lieu": "Salle B",
                "contenu": "Programme mis à jour",
                "observations": "",
                "statut": Seance.Statut.PLANIFIEE,
            },
        )

        self.assertRedirects(
            response,
            f"/o/centre-sessions-crud/formations/sessions/{self.session.pk}/",
            fetch_redirect_response=False,
        )
        self.seance.refresh_from_db()
        self.assertEqual(self.seance.titre, "Introduction avancée")
        self.assertEqual(self.seance.lieu, "Salle B")

    def test_delete_seance(self):
        seance = Seance.objects.create(
            organisation=self.organisation,
            session=self.session,
            titre="Séance à supprimer",
            date=date(2026, 8, 12),
            heure_debut=time(9, 0),
            heure_fin=time(11, 0),
        )

        response = self.client.post(
            f"/o/centre-sessions-crud/formations/seances/{seance.pk}/supprimer/"
        )

        self.assertRedirects(
            response,
            f"/o/centre-sessions-crud/formations/sessions/{self.session.pk}/",
            fetch_redirect_response=False,
        )
        self.assertFalse(Seance.objects.filter(pk=seance.pk).exists())
