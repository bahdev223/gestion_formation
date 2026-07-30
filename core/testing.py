"""Aides pour les tests qui ont besoin de modules optionnels actives.

Les modules optionnels (RH, paie, comptabilite, tresorerie, API) dependent du
plan d'abonnement. Un test qui cree une organisation nue n'y a donc pas acces :
ModuleAccessMiddleware renvoie 403. Ces helpers attachent un abonnement actif.
"""

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

TOUTES_FONCTIONNALITES = {
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
}


def souscrire_plan_complet(organisation):
    """Attache a l'organisation un abonnement actif ouvrant tous les modules."""
    from subscriptions.models import Abonnement, PlanAbonnement

    plan, cree = PlanAbonnement.objects.get_or_create(
        code=PlanAbonnement.Code.PRO,
        defaults={
            "nom": "Pro (tests)",
            "prix_mensuel": Decimal("95000"),
            "prix_annuel": Decimal("950000"),
            "max_utilisateurs": 1000,
            "max_participants": 100000,
            "max_formations_actives": 10000,
            "max_stockage_mo": 51200,
            "fonctionnalites": dict(TOUTES_FONCTIONNALITES),
        },
    )
    if not cree and plan.fonctionnalites != TOUTES_FONCTIONNALITES:
        # Un autre test a pu creer un plan PRO partiel : on garantit l'etat.
        plan.fonctionnalites = dict(TOUTES_FONCTIONNALITES)
        plan.save(update_fields=["fonctionnalites"])

    now = timezone.now()
    Abonnement.objects.update_or_create(
        organisation=organisation,
        defaults={
            "plan": plan,
            "statut": Abonnement.Statut.ACTIF,
            "date_debut": now - timedelta(days=1),
            "date_fin": now + timedelta(days=365),
            "montant": plan.prix_mensuel,
        },
    )
    return plan
