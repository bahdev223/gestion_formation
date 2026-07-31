"""Tests for formations views."""

from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from formations.models import CategorieFormation, Formation
from organisations.models import Organisation


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
