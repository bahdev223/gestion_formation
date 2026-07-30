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
