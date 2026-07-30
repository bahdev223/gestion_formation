"""Tests d'isolation inter-organisations.

Deux organisations A et B possedent chacune un jeu complet de donnees metier.
On verifie qu'un membre de A ne peut jamais atteindre les donnees de B, que ce
soit par une liste, un detail, un telechargement ou un identifiant devine.

Le middleware refuse deja l'acces a /o/<autre-slug>/ pour un non-membre. Les
tests ci-dessous vont plus loin : ils utilisent l'espace legitime de A en y
injectant des identifiants appartenant a B, ce qui est le seul moyen de
verifier que les querysets sont reellement filtres.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from documents.models import Attestation, DocumentGenere
from formations.models import CategorieFormation, Formation, Seance, SessionFormation
from inscriptions.models import Inscription
from organisations.models import MembreOrganisation, Organisation
from paiements.models import Paiement
from participants.models import Participant


def build_tenant(suffix, user):
    """Cree une organisation complete avec un jeu de donnees metier."""
    organisation = Organisation.objects.create(
        nom=f"Centre {suffix}",
        slug=f"centre-{suffix.lower()}",
        email=f"contact@{suffix.lower()}.test",
        telephone="+22300000000",
    )
    # CategorieFormation.nom est unique globalement : on suffixe pour eviter
    # une collision entre les deux organisations du test.
    categorie = CategorieFormation.objects.create(
        organisation=organisation,
        nom=f"Bureautique {suffix}",
    )
    formation = Formation.objects.create(
        organisation=organisation,
        nom=f"Excel {suffix}",
        categorie=categorie,
        duree=20,
        prix_standard=Decimal("100000"),
        statut=Formation.Statut.ACTIVE,
    )
    today = timezone.localdate()
    session = SessionFormation.objects.create(
        organisation=organisation,
        formation=formation,
        titre=f"Session {suffix}",
        formateur=user,
        date_debut=today,
        date_fin=today + timedelta(days=5),
        lieu=f"Salle {suffix}",
        prix_applique=Decimal("100000"),
        statut=SessionFormation.Statut.EN_COURS,
    )
    seance = Seance.objects.create(
        organisation=organisation,
        session=session,
        titre=f"Seance {suffix}",
        date=today,
        heure_debut="08:00",
        heure_fin="10:00",
    )
    participant = Participant.objects.create(
        organisation=organisation,
        nom=f"Nom{suffix}",
        prenom=f"Prenom{suffix}",
        telephone="+22370000000",
    )
    inscription = Inscription.objects.create(
        organisation=organisation,
        participant=participant,
        session=session,
        prix_initial=Decimal("100000"),
        montant_final=Decimal("100000"),
        statut=Inscription.Statut.TERMINE,
        cree_par=user,
    )
    paiement = Paiement.objects.create(
        organisation=organisation,
        inscription=inscription,
        montant=Decimal("100000"),
        mode_paiement=Paiement.ModePaiement.ESPECES,
        statut=Paiement.Statut.VALIDE,
        enregistre_par=user,
    )
    document = DocumentGenere.objects.create(
        organisation=organisation,
        type_document=DocumentGenere.TypeDocument.RECU,
        reference=f"REF-{suffix}",
        fichier=SimpleUploadedFile(f"recu-{suffix}.pdf", b"%PDF-1.4 test"),
        genere_par=user,
    )
    attestation = Attestation.objects.create(
        organisation=organisation,
        inscription=inscription,
        nom_participant=participant.nom_complet,
        nom_formation=formation.nom,
        titre_session=session.titre,
        date_debut=session.date_debut,
        date_fin=session.date_fin,
        duree_texte="20 heures",
        formateur_nom=user.get_username(),
        taux_presence=Decimal("100"),
        numero=f"ATT-{suffix}",
        fichier_pdf=SimpleUploadedFile(f"att-{suffix}.pdf", b"%PDF-1.4 test"),
        statut=Attestation.Statut.GENEREE,
        generee_par=user,
    )
    return {
        "organisation": organisation,
        "categorie": categorie,
        "formation": formation,
        "session": session,
        "seance": seance,
        "participant": participant,
        "inscription": inscription,
        "paiement": paiement,
        "document": document,
        "attestation": attestation,
    }


class TenantIsolationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        # Un utilisateur technique porte les FK obligatoires (formateur, auteur)
        # des deux jeux de donnees : il n'intervient pas dans les assertions.
        cls.fixture_user = User.objects.create_user(
            username="fixture-owner",
            email="fixture@test.test",
            password="test1234",
        )
        cls.a = build_tenant("Alpha", cls.fixture_user)
        cls.b = build_tenant("Beta", cls.fixture_user)

        cls.user_a = User.objects.create_user(
            username="membre-alpha",
            email="membre@alpha.test",
            password="test1234",
        )
        cls.user_a.user_permissions.set(Permission.objects.all())
        MembreOrganisation.objects.create(
            organisation=cls.a["organisation"],
            user=cls.user_a,
            role=MembreOrganisation.Role.ADMIN,
        )

    def setUp(self):
        self.client.force_login(self.user_a)

    # --- Listes -----------------------------------------------------------

    def test_les_listes_de_a_ne_contiennent_aucune_donnee_de_b(self):
        cases = [
            ("formations/", self.b["formation"].nom, self.a["formation"].nom),
            ("participants/", self.b["participant"].nom, self.a["participant"].nom),
            ("inscriptions/", self.b["inscription"].numero, self.a["inscription"].numero),
            # La liste des paiements affiche le numero de recu, pas le numero interne.
            (
                "paiements/",
                self.b["paiement"].numero_recu,
                self.a["paiement"].numero_recu,
            ),
            ("documents/", self.b["document"].reference, self.a["document"].reference),
            ("presences/", self.b["seance"].titre, self.a["seance"].titre),
        ]
        for path, foreign_marker, own_marker in cases:
            with self.subTest(path=path):
                response = self.client.get(f"/o/centre-alpha/{path}")
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, own_marker)
                self.assertNotContains(response, foreign_marker)

    # --- Details et telechargements avec un identifiant de B --------------

    def test_ouvrir_un_objet_de_b_depuis_lespace_de_a_renvoie_404(self):
        cases = [
            f"formations/sessions/{self.b['session'].pk}/",
            f"paiements/{self.b['paiement'].pk}/",
            f"presences/seances/{self.b['seance'].pk}/",
            f"documents/telecharger/{self.b['document'].pk}/",
            f"documents/attestations/{self.b['attestation'].pk}/telecharger/",
        ]
        for path in cases:
            with self.subTest(path=path):
                response = self.client.get(f"/o/centre-alpha/{path}")
                self.assertIn(response.status_code, (403, 404))

    def test_les_memes_objets_de_a_restent_accessibles(self):
        cases = [
            f"formations/sessions/{self.a['session'].pk}/",
            f"paiements/{self.a['paiement'].pk}/",
            f"presences/seances/{self.a['seance'].pk}/",
            f"documents/telecharger/{self.a['document'].pk}/",
            f"documents/attestations/{self.a['attestation'].pk}/telecharger/",
        ]
        for path in cases:
            with self.subTest(path=path):
                response = self.client.get(f"/o/centre-alpha/{path}")
                self.assertEqual(response.status_code, 200)

    # --- Ecritures croisees ----------------------------------------------

    def test_generer_un_recu_pour_un_paiement_de_b_est_refuse(self):
        response = self.client.post(
            "/o/centre-alpha/documents/generer/recu/",
            {"paiement_id": self.b["paiement"].pk},
        )
        self.assertIn(response.status_code, (403, 404))
        self.assertFalse(
            DocumentGenere.objects.filter(
                organisation=self.a["organisation"],
                reference=self.b["paiement"].numero_recu,
            ).exists()
        )

    def test_generer_une_attestation_pour_une_inscription_de_b_est_refuse(self):
        response = self.client.post(
            "/o/centre-alpha/documents/generer/attestation/",
            {"inscription_id": self.b["inscription"].pk},
        )
        self.assertIn(response.status_code, (403, 404))

    def test_inscrire_un_participant_de_b_dans_une_session_de_a_est_refuse(self):
        response = self.client.post(
            "/o/centre-alpha/inscriptions/create/",
            {
                "participant": self.b["participant"].pk,
                "session": self.a["session"].pk,
                "date_inscription": timezone.localdate().isoformat(),
                "prix_initial": "100000",
                "remise": "0",
                "statut": Inscription.Statut.PREINSCRIT,
            },
        )
        self.assertNotIn(response.status_code, (301, 302))
        self.assertFalse(
            Inscription.objects.filter(
                participant=self.b["participant"],
                session=self.a["session"],
            ).exists()
        )

    # --- Acces a un espace dont on n'est pas membre -----------------------

    def test_un_non_membre_ne_peut_pas_entrer_dans_lespace_de_b(self):
        for path in ("dashboard/", "formations/", "paiements/", "comptabilite/"):
            with self.subTest(path=path):
                response = self.client.get(f"/o/centre-beta/{path}")
                self.assertIn(response.status_code, (403, 404))


class MissingTenantContextTest(TestCase):
    """Sans contexte organisation, une vue metier doit refuser, pas retomber
    silencieusement sur une organisation par defaut."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            username="orphan-admin",
            email="orphan@test.test",
            password="test1234",
        )

    def test_require_request_organisation_leve_une_erreur_sans_tenant(self):
        from django.core.exceptions import PermissionDenied
        from django.test import RequestFactory

        from organisations.utils import require_request_organisation

        request = RequestFactory().get("/")
        with self.assertRaises(PermissionDenied):
            require_request_organisation(request)

    def test_aucune_organisation_par_defaut_nest_exposee(self):
        from organisations.utils import get_user_default_organisation

        # L'utilisateur n'est membre d'aucune organisation : meme superuser,
        # il ne doit heriter d'aucun tenant implicite.
        self.assertIsNone(get_user_default_organisation(self.user))
