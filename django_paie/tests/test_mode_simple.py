import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from ..models import EcheanceSalariale, PeriodePaie
from ..services import ModeSimpleService
from ..utils import (
    est_periode_valide,
    extraire_mois_annee,
    generer_periodes_annee,
    periode_en_cours,
)


class ModeSimpleServiceTest(TestCase):
    def setUp(self):
        self.employe = get_user_model().objects.create_user(
            username="moussa", password="test123"
        )
        self.service = ModeSimpleService()

    def test_creer_echeance(self):
        echeance = self.service.creer_echeance(
            employe=self.employe,
            periode="07/2026",
            montant_brut=50000,
            montant_net=50000,
        )
        self.assertEqual(echeance.montant_brut, 50000)
        self.assertEqual(echeance.montant_net, 50000)
        self.assertEqual(echeance.mois, 7)
        self.assertEqual(echeance.annee, 2026)
        self.assertEqual(echeance.periode, "07/2026")
        self.assertEqual(echeance.statut, "A_PAYER")
        self.assertEqual(echeance.mode, "SIMPLE")

    def test_echeance_unique_par_periode(self):
        self.service.creer_echeance(self.employe, "07/2026", 50000)
        echeance2 = self.service.creer_echeance(self.employe, "07/2026", 60000)
        self.assertEqual(echeance2.montant_brut, 60000)
        count = EcheanceSalariale.objects.filter(mois=7, annee=2026).count()
        self.assertEqual(count, 1)

    def test_enregistrer_paiement_total(self):
        echeance = self.service.creer_echeance(self.employe, "07/2026", 50000)
        paiement = self.service.enregistrer_paiement(
            echeance_id=echeance.id, montant=50000
        )
        echeance.refresh_from_db()
        self.assertEqual(echeance.montant_paye, 50000)
        self.assertEqual(echeance.statut, "PAYE")
        self.assertEqual(paiement.type_paiement, "PAIEMENT")

    def test_enregistrer_paiement_accepte_montant_chaine(self):
        echeance = self.service.creer_echeance(self.employe, "07/2026", 50000)
        self.service.enregistrer_paiement(echeance_id=echeance.id, montant="50000")
        echeance.refresh_from_db()
        self.assertEqual(echeance.montant_paye, Decimal("50000"))
        self.assertEqual(echeance.statut, "PAYE")

    def test_enregistrer_paiement_partiel(self):
        echeance = self.service.creer_echeance(
            self.employe, "09/2026", 50000, date_echeance=date(2026, 9, 30),
        )
        self.service.enregistrer_paiement(
            echeance.id, 20000, date_paiement=date(2026, 9, 15),
        )
        echeance.refresh_from_db()
        self.assertEqual(echeance.montant_paye, 20000)
        self.assertEqual(echeance.statut, "PARTIELLEMENT_PAYE")

    def test_mois_impayes(self):
        self.service.creer_echeance(self.employe, "06/2026", 50000)
        self.service.creer_echeance(self.employe, "07/2026", 50000)
        echeance_aout = self.service.creer_echeance(self.employe, "08/2026", 50000)
        self.service.enregistrer_paiement(echeance_aout.id, 50000)

        impayes = self.service.mois_impayes(self.employe, annee=2026)
        self.assertEqual(len(impayes), 2)

    def test_reste_a_payer(self):
        echeance = self.service.creer_echeance(self.employe, "07/2026", 50000)
        self.assertEqual(echeance.reste_a_payer, 50000)
        self.service.enregistrer_paiement(echeance.id, 30000)
        echeance.refresh_from_db()
        self.assertEqual(echeance.reste_a_payer, 20000)

    def test_dashboard(self):
        e = self.service.creer_echeance(self.employe, "07/2026", 50000)
        self.service.enregistrer_paiement(e.id, 50000)
        dash = self.service.dashboard(annee=2026)
        self.assertEqual(dash["total_echeances"], 1)
        self.assertEqual(dash["paye"], 1)

    def test_payer_plusieurs_mois(self):
        self.service.creer_echeance(self.employe, "07/2026", 50000)
        self.service.creer_echeance(self.employe, "08/2026", 50000)
        resultat = self.service.payer_plusieurs_mois(
            self.employe, 80000, "07/2026", "08/2026"
        )
        paiements = resultat["paiements"]
        self.assertEqual(len(paiements), 2)
        self.assertEqual(paiements[0].montant, 50000)
        self.assertEqual(paiements[1].montant, 30000)
        self.assertEqual(resultat["montant_affecte"], Decimal("80000"))
        self.assertEqual(resultat["reliquat"], Decimal("0"))

    def test_payer_plusieurs_mois_retourne_reliquat(self):
        self.service.creer_echeance(self.employe, "07/2026", 50000)
        self.service.creer_echeance(self.employe, "08/2026", 50000)
        resultat = self.service.payer_plusieurs_mois(
            self.employe, 120000, "07/2026", "08/2026"
        )
        self.assertEqual(resultat["montant_affecte"], Decimal("100000"))
        self.assertEqual(resultat["reliquat"], Decimal("20000"))

    def test_creer_echeance_negative_refusee(self):
        with self.assertRaises(ValueError):
            self.service.creer_echeance(self.employe, "07/2026", -50000)

    def test_creer_echeance_refuse_annee_sur_deux_chiffres(self):
        with self.assertRaisesRegex(ValueError, "année entre 2000 et 2100"):
            self.service.creer_echeance(self.employe, "07/26", 50000)
        self.assertFalse(EcheanceSalariale.objects.exists())

    def test_montant_zero_rejete(self):
        echeance = self.service.creer_echeance(self.employe, "07/2026", 50000)
        with self.assertRaises(ValueError):
            self.service.enregistrer_paiement(echeance.id, 0)

    def test_trop_percu(self):
        echeance = self.service.creer_echeance(self.employe, "07/2026", 50000)
        self.service.enregistrer_paiement(echeance.id, 60000)
        echeance.refresh_from_db()
        self.assertEqual(echeance.statut, "TROPPERCU")
        self.assertEqual(echeance.trop_percu, 10000)

    def test_avance_conserve_salaire_complet(self):
        source = self.service.creer_echeance(self.employe, "07/2026", montant_brut=50000, montant_net=48000)
        paiement = self.service.enregistrer_paiement(
            echeance_id=source.id, montant=20000, type_paiement="AVANCE",
        )
        echeance_cible = paiement.echeance
        self.assertEqual(echeance_cible.mois, 8)
        self.assertEqual(echeance_cible.annee, 2026)
        self.assertEqual(echeance_cible.montant_brut, 50000)
        self.assertEqual(echeance_cible.montant_net, 48000)
        self.assertEqual(echeance_cible.montant_paye, 20000)
        self.assertEqual(echeance_cible.statut, "PAYE_EN_AVANCE")

    def test_avance_devient_payee_quand_la_periode_arrive(self):
        source = self.service.creer_echeance(
            self.employe, "07/2026", montant_brut=50000, montant_net=50000
        )
        paiement = self.service.enregistrer_paiement(
            echeance_id=source.id,
            montant=50000,
            type_paiement="AVANCE",
            date_paiement=date(2026, 7, 10),
        )
        echeance_cible = paiement.echeance
        self.assertEqual(echeance_cible.statut, "PAYE_EN_AVANCE")
        with patch("django_paie.models.echeance.date") as date_mock:
            date_mock.today.return_value = date(2026, 8, 1)
            echeance_cible.mettre_a_jour_statut()
        echeance_cible.refresh_from_db()
        self.assertEqual(echeance_cible.statut, "PAYE")

    def test_annulation_paiement(self):
        echeance = self.service.creer_echeance(self.employe, "07/2026", 50000)
        paiement = self.service.enregistrer_paiement(echeance.id, 50000)
        echeance.refresh_from_db()
        self.assertEqual(echeance.statut, "PAYE")
        paiement.annuler()
        paiement.refresh_from_db()
        self.assertEqual(paiement.statut, "ANNULE")
        echeance.refresh_from_db()
        self.assertEqual(echeance.montant_paye, 0)
        self.assertIn(echeance.statut, ["A_PAYER", "EN_RETARD"])

    def test_paiement_valide_ne_peut_pas_etre_deplace(self):
        echeance_1 = self.service.creer_echeance(self.employe, "07/2026", 50000)
        echeance_2 = self.service.creer_echeance(self.employe, "08/2026", 50000)
        paiement = self.service.enregistrer_paiement(echeance_1.id, 50000)
        paiement.echeance = echeance_2
        with self.assertRaises(ValueError):
            paiement.save()

    def test_arriere_detecte_automatiquement(self):
        echeance = self.service.creer_echeance(self.employe, "06/2026", 50000)
        echeance.date_fin = date(2026, 6, 30)
        echeance.save()
        paiement = self.service.enregistrer_paiement(
            echeance.id, 50000, date_paiement=date(2026, 7, 15),
        )
        self.assertEqual(paiement.type_paiement, "ARRIERE")

    def test_creer_echeance_periode_close_refuse(self):
        periode = PeriodePaie.from_libelle("06/2026")
        periode.est_cloturee = True
        periode.save()
        with self.assertRaises(ValueError):
            self.service.creer_echeance(self.employe, "06/2026", 50000)

    def test_creer_echeance_deja_payee_refuse(self):
        echeance = self.service.creer_echeance(self.employe, "07/2026", 50000)
        self.service.enregistrer_paiement(echeance.id, 50000)
        with self.assertRaises(ValueError):
            self.service.creer_echeance(self.employe, "07/2026", 60000)

    def test_paiement_periode_close_refuse(self):
        echeance = self.service.creer_echeance(self.employe, "07/2026", 50000)
        periode = PeriodePaie.from_libelle("07/2026")
        periode.est_cloturee = True
        periode.save(update_fields=["est_cloturee"])
        with self.assertRaises(ValueError):
            self.service.enregistrer_paiement(echeance.id, 10000)

    def test_avance_sans_salaire_reference_refusee(self):
        with self.assertRaisesRegex(ValueError, "salaire de référence"):
            self.service.enregistrer_paiement(
                employe=self.employe,
                periode="07/2026",
                montant=20000,
                type_paiement="AVANCE",
            )

    def test_avance_accepte_montant_mensuel_explicite(self):
        paiement = self.service.enregistrer_paiement(
            employe=self.employe,
            periode="07/2026",
            montant=20000,
            montant_mensuel=50000,
            type_paiement="AVANCE",
        )
        self.assertEqual(paiement.echeance.montant_net, 50000)
        self.assertEqual(paiement.echeance.reste_a_payer, 30000)

    def test_isolation_multi_entreprise(self):
        service_b = ModeSimpleService(entreprise_id="ENT-B")
        e_a = self.service.creer_echeance(self.employe, "07/2026", 50000)
        e_b = service_b.creer_echeance(self.employe, "07/2026", 70000)
        self.assertNotEqual(e_a.pk, e_b.pk)
        self.assertEqual(e_a.montant_brut, 50000)
        self.assertEqual(e_b.montant_brut, 70000)
        dash_a = self.service.dashboard(annee=2026)
        dash_b = service_b.dashboard(annee=2026)
        self.assertEqual(dash_a["total_echeances"], 1)
        self.assertEqual(dash_b["total_echeances"], 1)


class UtilsTest(TestCase):
    def test_generer_periodes(self):
        periodes = generer_periodes_annee(2026)
        self.assertEqual(len(periodes), 12)
        self.assertEqual(periodes[0], "01/2026")
        self.assertEqual(periodes[11], "12/2026")

    def test_periode_en_cours(self):
        p = periode_en_cours()
        self.assertTrue(est_periode_valide(p))

    def test_est_periode_valide(self):
        self.assertTrue(est_periode_valide("07/2026"))
        self.assertFalse(est_periode_valide("13/2026"))
        self.assertFalse(est_periode_valide("07/99"))
        self.assertFalse(est_periode_valide(""))

    def test_extraire_mois_annee(self):
        m, a = extraire_mois_annee("07/2026")
        self.assertEqual(m, 7)
        self.assertEqual(a, 2026)
        with self.assertRaises(ValueError):
            extraire_mois_annee("")


class PeriodePaieModelTest(TestCase):
    def test_from_libelle(self):
        p = PeriodePaie.from_libelle("07/2026")
        self.assertEqual(p.mois, 7)
        self.assertEqual(p.annee, 2026)
        self.assertEqual(p.date_debut.month, 7)
        self.assertEqual(p.date_debut.day, 1)

    def test_date_fin_correcte(self):
        p = PeriodePaie.from_libelle("01/2026")
        self.assertEqual(p.date_fin.day, 31)
        p = PeriodePaie.from_libelle("02/2026")
        self.assertEqual(p.date_fin.day, 28)
        p = PeriodePaie.from_libelle("07/2026")
        self.assertEqual(p.date_fin.day, 31)

    def test_from_libelle_reutilise(self):
        p1 = PeriodePaie.from_libelle("07/2026")
        p2 = PeriodePaie.from_libelle("07/2026")
        self.assertEqual(p1.pk, p2.pk)


class APITest(TestCase):
    def setUp(self):
        from organisations.models import Organisation

        self.employe = get_user_model().objects.create_user(
            username="api_test", password="test123", is_staff=True,
        )
        # Les API de paie sont isolees par organisation : le tenant vient de
        # l'URL /o/<slug>/, et entreprise_id vaut le slug de l'organisation.
        self.organisation = Organisation.objects.create(
            nom="Centre Paie",
            slug="centre-paie",
            email="paie@test.test",
            telephone="+22300000000",
        )
        self.service = ModeSimpleService(entreprise_id=self.organisation.slug)

    def _api_request(self, method, path, data=None, organisation=...):
        from django.test import RequestFactory
        factory = RequestFactory()
        if method == "GET":
            request = factory.get(path)
        else:
            request = factory.post(path, json.dumps(data), content_type="application/json")
        self.employe.is_superuser = True
        self.employe.save(update_fields=["is_superuser"])
        request.user = self.employe
        # RequestFactory ne passe pas par le middleware tenant : on pose
        # l'organisation a la main, comme le ferait /o/<slug>/.
        request.organisation = (
            self.organisation if organisation is ... else organisation
        )
        return request

    def test_api_echeance_list(self):
        from ..api.views import EcheanceListAPI
        request = self._api_request("GET", "/api/echeances/")
        response = EcheanceListAPI.as_view()(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("data", data)
        self.assertIn("count", data)

    def test_api_paiement_create(self):
        from ..api.views import PaiementListAPI
        echeance = self.service.creer_echeance(self.employe, "07/2026", 50000)
        request = self._api_request("POST", "/api/paiements/",
                                    {"echeance_id": echeance.id, "montant": 50000})
        response = PaiementListAPI.as_view()(request)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertEqual(data["data"]["montant"], 50000)

    def test_api_cloture_refuse_si_autre_echeance_impayee(self):
        from ..api.views import EcheanceDetailAPI
        autre = get_user_model().objects.create_user(username="autre")
        echeance_payee = self.service.creer_echeance(self.employe, "07/2026", 50000)
        self.service.creer_echeance(autre, "07/2026", 50000)
        self.service.enregistrer_paiement(echeance_payee.id, 50000)
        request = self._api_request(
            "POST", f"/api/echeances/{echeance_payee.id}/", {"action": "cloturer"}
        )
        response = EcheanceDetailAPI.as_view()(request, pk=echeance_payee.id)
        self.assertEqual(response.status_code, 400)

    def test_api_refuse_utilisateur_sans_permission(self):
        from ..api.views import EcheanceListAPI
        request = self._api_request("GET", "/api/echeances/")
        self.employe.is_superuser = False
        self.employe.role = "FORMATEUR"
        self.employe.save(update_fields=["is_superuser", "role"])
        with self.assertRaises(PermissionDenied):
            EcheanceListAPI.as_view()(request)

    def test_api_refuse_sans_contexte_organisation(self):
        """Sans tenant, l'API doit refuser au lieu de tout renvoyer."""
        from ..api.views import EcheanceListAPI
        request = self._api_request("GET", "/api/echeances/", organisation=None)
        with self.assertRaises(PermissionDenied):
            EcheanceListAPI.as_view()(request)

    def test_api_nexpose_pas_les_echeances_dune_autre_organisation(self):
        from organisations.models import Organisation

        from ..api.views import EcheanceListAPI

        voisin = Organisation.objects.create(
            nom="Centre Voisin", slug="centre-voisin",
            email="voisin@test.test", telephone="+22300000001",
        )
        ModeSimpleService(entreprise_id=voisin.slug).creer_echeance(
            self.employe, "07/2026", 90000
        )

        request = self._api_request("GET", "/api/echeances/")
        response = EcheanceListAPI.as_view()(request)
        payload = json.loads(response.content)
        self.assertEqual(payload["count"], 0)


class StatistiquesPaieServiceTest(TestCase):
    def setUp(self):
        self.employe = get_user_model().objects.create_user(
            username="fatou", password="test123"
        )
        self.entreprise_id = "stats-test"
        self.service = ModeSimpleService(entreprise_id=self.entreprise_id)

    def test_organisation_est_obligatoire(self):
        from django.core.exceptions import PermissionDenied

        from ..services import StatistiquesPaieService

        with self.assertRaises(PermissionDenied):
            StatistiquesPaieService(entreprise_id="")

    def test_arrieres_ignore_partiel_avant_date(self):
        echeance = self.service.creer_echeance(self.employe, "09/2026", 50000)
        echeance.date_echeance = date(2026, 9, 30)
        echeance.save()
        self.service.enregistrer_paiement(echeance.id, 20000)
        from ..services import StatistiquesPaieService
        stats = StatistiquesPaieService(entreprise_id=self.entreprise_id)
        arrieres = stats.arrieres()
        self.assertEqual(arrieres["nombre_echeances"], 0)

    def test_resume_annuel_reste_global_non_negatif(self):
        echeance = self.service.creer_echeance(self.employe, "07/2026", 50000)
        self.service.enregistrer_paiement(echeance.id, 60000)
        from ..services import StatistiquesPaieService
        stats = StatistiquesPaieService(entreprise_id=self.entreprise_id)
        resume = stats.resume_annuel(annee=2026)
        self.assertEqual(resume["reste_global"], 0)
        self.assertEqual(resume["total_montant_du"], 50000)
        self.assertEqual(resume["total_montant_paye"], 60000)


class PaiementBulletinPDFViewTest(TestCase):
    def setUp(self):
        from organisations.models import Organisation

        self.user = get_user_model().objects.create_superuser(
            username="paie-pdf-admin",
            email="paie-pdf@example.com",
            password="test123",
        )
        self.organisation = Organisation.objects.create(
            nom="Entreprise Paie PDF",
            slug="entreprise-paie-pdf",
            email="paie-pdf@entreprise.test",
            telephone="+22370000003",
        )
        # Le module paie est optionnel : sans abonnement l'acces est refuse.
        from core.testing import souscrire_plan_complet

        souscrire_plan_complet(self.organisation)
        self.service = ModeSimpleService(entreprise_id=self.organisation.slug)
        self.client.force_login(self.user)

    def test_telecharger_bulletin_pdf_apres_paiement(self):
        echeance = self.service.creer_echeance(self.user, "07/2026", 150000)
        paiement = self.service.enregistrer_paiement(echeance.id, 150000)

        response = self.client.get(
            reverse(
                "organisations:paie:paiement-bulletin",
                kwargs={
                    "organisation_slug": self.organisation.slug,
                    "pk": paiement.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_creation_paiement_redirige_vers_bulletin_pdf(self):
        echeance = self.service.creer_echeance(self.user, "07/2026", 150000)

        response = self.client.post(
            reverse(
                "organisations:paie:paiement-create",
                kwargs={"organisation_slug": self.organisation.slug},
            ),
            {
                "echeance": echeance.pk,
                "montant": "150000",
                "type_paiement": "PAIEMENT",
                "date_paiement": "2026-07-30",
                "notes": "",
            },
        )

        paiement = echeance.paiements.get()
        self.assertRedirects(
            response,
            reverse(
                "organisations:paie:paiement-bulletin",
                kwargs={
                    "organisation_slug": self.organisation.slug,
                    "pk": paiement.pk,
                },
            ),
            fetch_redirect_response=False,
        )
