from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from organisations.models import MembreOrganisation, Organisation
from subscriptions.models import Abonnement, PlanAbonnement

PLANS = [
    {
        "code": PlanAbonnement.Code.STARTER,
        "nom": "Starter",
        "description": "Pour les petits centres de formation.",
        "prix_mensuel": Decimal("15000"),
        "prix_annuel": Decimal("150000"),
        "max_utilisateurs": 3,
        "max_participants": 500,
        "max_formations_actives": 10,
        "max_stockage_mo": 1024,
        "ordre": 1,
        "fonctionnalites": {
            "formations": True,
            "sessions": True,
            "participants": True,
            "inscriptions": True,
            "participant_payments": True,
            "presences": True,
            "receipts_pdf": True,
            "simple_attestations": True,
            "custom_documents": False,
            "advanced_exports": False,
            "advanced_reports": False,
            "notifications": False,
            "api": False,
            "custom_domain": False,
            # Modules de gestion d'entreprise : reserves aux paliers superieurs.
            "hr": False,
            "payroll": False,
            "accounting": False,
            "treasury": False,
        },
    },
    {
        "code": PlanAbonnement.Code.PREMIUM,
        "nom": "Premium",
        "description": "Pour les centres structures avec rapports et documents avances.",
        "prix_mensuel": Decimal("45000"),
        "prix_annuel": Decimal("450000"),
        "max_utilisateurs": 10,
        "max_participants": 5000,
        "max_formations_actives": 100,
        "max_stockage_mo": 10240,
        "ordre": 2,
        "fonctionnalites": {
            "formations": True,
            "sessions": True,
            "participants": True,
            "inscriptions": True,
            "participant_payments": True,
            "presences": True,
            "receipts_pdf": True,
            "simple_attestations": True,
            "custom_documents": True,
            "advanced_exports": True,
            "advanced_reports": True,
            "notifications": True,
            "api": False,
            "custom_domain": False,
            "hr": False,
            "payroll": False,
            "accounting": True,
            "treasury": True,
        },
    },
    {
        "code": PlanAbonnement.Code.PRO,
        "nom": "Pro",
        "description": "Pour les grandes entreprises, reseaux et integrations.",
        "prix_mensuel": Decimal("95000"),
        "prix_annuel": Decimal("950000"),
        "max_utilisateurs": 100,
        "max_participants": 100000,
        "max_formations_actives": 1000,
        "max_stockage_mo": 51200,
        "ordre": 3,
        "fonctionnalites": {
            "formations": True,
            "sessions": True,
            "participants": True,
            "inscriptions": True,
            "participant_payments": True,
            "presences": True,
            "receipts_pdf": True,
            "simple_attestations": True,
            "custom_documents": True,
            "advanced_exports": True,
            "advanced_reports": True,
            "notifications": True,
            "multi_agency": True,
            "custom_roles": True,
            "complete_audit": True,
            "api": True,
            "custom_domain": True,
            "hr": True,
            "payroll": True,
            "accounting": True,
            "treasury": True,
        },
    },
]


class Command(BaseCommand):
    help = "Cree les plans SaaS et l'organisation cliente BALY'S GROUP."

    def handle(self, *args, **options):
        plans = {}
        for payload in PLANS:
            code = payload["code"]
            plan, _ = PlanAbonnement.objects.update_or_create(
                code=code,
                defaults=payload,
            )
            plans[code] = plan

        organisation, _ = Organisation.objects.update_or_create(
            slug="balys-group",
            defaults={
                "nom": "BALY'S GROUP",
                "email": "contact@balysgroup.com",
                "telephone": "+223 00 00 00 00",
                "pays": "Mali",
                "devise": "FCFA",
                "statut": Organisation.Statut.ACTIVE,
                "is_active": True,
            },
        )

        now = timezone.now()
        Abonnement.objects.update_or_create(
            organisation=organisation,
            defaults={
                "plan": plans[PlanAbonnement.Code.PRO],
                "cycle": Abonnement.Cycle.MENSUEL,
                "statut": Abonnement.Statut.ACTIF,
                "date_debut": now,
                "date_fin": now + timedelta(days=30),
                "renouvellement_automatique": False,
                "montant": plans[PlanAbonnement.Code.PRO].prix_mensuel,
                "jours_grace": 3,
            },
        )

        User = get_user_model()
        owner = User.objects.filter(username="admin").first()
        if owner:
            MembreOrganisation.objects.update_or_create(
                organisation=organisation,
                user=owner,
                defaults={
                    "role": MembreOrganisation.Role.PROPRIETAIRE,
                    "is_active": True,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Plans SaaS crees et BALY'S GROUP configure comme premiere organisation."
            )
        )
