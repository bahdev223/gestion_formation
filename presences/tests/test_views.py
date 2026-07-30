from django.urls import reverse

from presences.models import Presence

from .test_services import PresenceServiceTest as _PresenceServiceTest


class PresenceViewTest(_PresenceServiceTest):
    def test_feuille_accessible_et_enregistrable(self):
        self.client.force_login(self.user)
        url = reverse(
            "organisations:presences:sheet",
            kwargs={
                "organisation_slug": self.organisation.slug,
                "seance_id": self.seance.pk,
            },
        )
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(
            url,
            {
                f"statut_{self.inscription.pk}": Presence.Statut.PRESENT,
                f"heure_arrivee_{self.inscription.pk}": "09:00",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Presence.objects.filter(
                seance=self.seance, inscription=self.inscription
            ).exists()
        )
