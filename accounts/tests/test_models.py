from django.contrib.auth import get_user_model
from django.test import TestCase


class UserRoleTest(TestCase):
    def test_superutilisateur_recoit_role_administrateur(self):
        user = get_user_model().objects.create_superuser(
            username="admin-test",
            email="admin@example.com",
            password="test1234",
        )
        user.refresh_from_db()
        self.assertEqual(user.role, "ADMIN")
        self.assertTrue(user.groups.filter(name="Administrateurs").exists())

    def test_responsable_recoit_son_groupe_et_permissions(self):
        user = get_user_model().objects.create_user(
            username="responsable-test",
            role="RESPONSABLE",
            password="test1234",
        )
        self.assertTrue(
            user.groups.filter(name="Responsables formation").exists()
        )
        self.assertTrue(user.has_perm("formations.add_formation"))
        self.assertTrue(user.has_perm("operations.view_operation"))

    def test_changement_role_remplace_groupe_gere(self):
        user = get_user_model().objects.create_user(
            username="comptable-test",
            role="COMPTABLE",
            password="test1234",
        )
        user.role = "CAISSIER"
        user.save(update_fields=["role"])
        self.assertTrue(user.groups.filter(name="Caissiers").exists())
        self.assertFalse(user.groups.filter(name="Comptables").exists())
