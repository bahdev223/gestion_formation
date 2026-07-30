from decimal import Decimal

DEFAULT_PLANS = [
    {
        "code": "STARTER",
        "nom": "Basic",
        "description": "Pour les petits centres de formation.",
        "prix_mensuel": Decimal("15000"),
        "prix_annuel": Decimal("150000"),
        "max_utilisateurs": 3,
        "max_participants": 500,
        "max_formations_actives": 10,
        "max_stockage_mo": 1024,
        "ordre": 1,
        "is_active": True,
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
            "hr": False,
            "payroll": False,
            "accounting": False,
            "treasury": False,
        },
    },
    {
        "code": "PREMIUM",
        "nom": "Business",
        "description": "Pour les centres structurés avec rapports et documents avancés.",
        "prix_mensuel": Decimal("45000"),
        "prix_annuel": Decimal("450000"),
        "max_utilisateurs": 10,
        "max_participants": 5000,
        "max_formations_actives": 100,
        "max_stockage_mo": 10240,
        "ordre": 2,
        "is_active": True,
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
        "code": "PRO",
        "nom": "Enterprise",
        "description": "Pour les grandes entreprises, réseaux et intégrations.",
        "prix_mensuel": Decimal("95000"),
        "prix_annuel": Decimal("950000"),
        "max_utilisateurs": 100,
        "max_participants": 100000,
        "max_formations_actives": 1000,
        "max_stockage_mo": 51200,
        "ordre": 3,
        "is_active": True,
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


def ensure_default_plans(*, update_existing=False):
    from subscriptions.models import PlanAbonnement

    plans = {}
    created_codes = []
    for definition in DEFAULT_PLANS:
        payload = dict(definition)
        payload["fonctionnalites"] = dict(definition["fonctionnalites"])
        code = payload.pop("code")
        if update_existing:
            plan, created = PlanAbonnement.objects.update_or_create(
                code=code,
                defaults=payload,
            )
        else:
            plan, created = PlanAbonnement.objects.get_or_create(
                code=code,
                defaults=payload,
            )
        plans[code] = plan
        if created:
            created_codes.append(code)
    return plans, created_codes
