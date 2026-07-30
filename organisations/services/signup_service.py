from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from subscriptions.models import Abonnement, PlanAbonnement

from ..models import MembreOrganisation, Organisation


def get_or_create_trial_plan():
    plan, _ = PlanAbonnement.objects.get_or_create(
        code=PlanAbonnement.Code.STARTER,
        defaults={
            "nom": "Basic",
            "description": "Plan d'essai pour démarrer la gestion de formation.",
            "prix_mensuel": 0,
            "prix_annuel": 0,
            "max_utilisateurs": 3,
            "max_participants": 200,
            "max_formations_actives": 10,
            "max_stockage_mo": 512,
            "fonctionnalites": {
                "formations": True,
                "paiements": True,
                "documents_pdf": True,
                "rh": False,
                "comptabilite": False,
            },
            "ordre": 1,
        },
    )
    return plan


@transaction.atomic
def create_organisation_account(cleaned_data):
    organisation = Organisation.objects.create(
        nom=cleaned_data["organisation_nom"],
        slug=slugify(cleaned_data["organisation_nom"]),
        email=cleaned_data["organisation_email"],
        telephone=cleaned_data["organisation_telephone"],
        ville=cleaned_data.get("ville", ""),
        pays=cleaned_data.get("pays") or "Mali",
        statut=Organisation.Statut.ESSAI,
        is_active=True,
    )

    user = get_user_model().objects.create_user(
        username=cleaned_data["matricule"],
        email=cleaned_data["email"],
        password=cleaned_data["password1"],
        first_name=cleaned_data["first_name"],
        last_name=cleaned_data["last_name"],
        role="ADMIN",
    )

    MembreOrganisation.objects.create(
        organisation=organisation,
        user=user,
        role=MembreOrganisation.Role.PROPRIETAIRE,
    )

    trial_days = 14
    date_debut = timezone.now()
    Abonnement.objects.create(
        organisation=organisation,
        plan=get_or_create_trial_plan(),
        cycle=Abonnement.Cycle.MENSUEL,
        statut=Abonnement.Statut.ESSAI,
        date_debut=date_debut,
        date_fin=date_debut + timedelta(days=trial_days),
        montant=0,
    )

    return organisation, user
