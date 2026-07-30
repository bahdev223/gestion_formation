import shutil
from datetime import timedelta
from decimal import Decimal
from time import perf_counter
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.db.models import Count, Max, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.text import slugify

from formations.models import Formation
from organisations.models import MembreOrganisation, Organisation
from participants.models import Participant
from subscriptions.models import Abonnement, PaiementAbonnement

from .models import (
    BackupRecord,
    PlatformAuditEvent,
    SupportTicket,
    SystemMetric,
)


def get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR") or None


def log_platform_event(
    request,
    event_type,
    description,
    *,
    organisation=None,
    severity=PlatformAuditEvent.Severite.INFO,
    object_type="",
    object_id="",
    metadata=None,
):
    return PlatformAuditEvent.objects.create(
        organisation=organisation,
        acteur=request.user if request.user.is_authenticated else None,
        type_evenement=event_type,
        severite=severity,
        description=description,
        adresse_ip=get_client_ip(request),
        objet_type=object_type,
        objet_id=str(object_id or ""),
        metadata=metadata or {},
    )


def organisation_queryset():
    return (
        Organisation.objects.select_related("abonnement", "abonnement__plan")
        .annotate(
            utilisateurs_count=Count(
                "membres",
                filter=Q(membres__is_active=True),
                distinct=True,
            ),
            derniere_connexion=Max("membres__user__last_login"),
        )
        .order_by("-created_at")
    )


def calculate_mrr():
    total = Decimal("0")
    abonnements = Abonnement.objects.filter(
        statut=Abonnement.Statut.ACTIF
    ).only("cycle", "montant")
    for abonnement in abonnements:
        if abonnement.cycle == Abonnement.Cycle.ANNUEL:
            total += abonnement.montant / Decimal("12")
        else:
            total += abonnement.montant
    return total


def platform_dashboard_stats():
    today = timezone.localdate()
    last_30_days = timezone.now() - timezone.timedelta(days=30)
    organisations = Organisation.objects.all()
    mrr = calculate_mrr()
    active_subscriptions = Abonnement.objects.filter(
        statut=Abonnement.Statut.ACTIF
    )
    cancelled = Abonnement.objects.filter(
        statut=Abonnement.Statut.ANNULE,
        updated_at__gte=last_30_days,
    ).count()
    denominator = active_subscriptions.count() + cancelled
    churn = (cancelled / denominator * 100) if denominator else 0

    return {
        "organisations_total": organisations.count(),
        "organisations_actives": organisations.filter(
            statut=Organisation.Statut.ACTIVE,
            is_active=True,
        ).count(),
        "essais": organisations.filter(statut=Organisation.Statut.ESSAI).count(),
        "premium": active_subscriptions.filter(
            plan__code="PREMIUM"
        ).count(),
        "pro": active_subscriptions.filter(plan__code="PRO").count(),
        "mrr": mrr,
        "arr": mrr * Decimal("12"),
        "churn": churn,
        "nouveaux_clients": organisations.filter(
            created_at__gte=last_30_days
        ).count(),
        "connexions_aujourdhui": PlatformAuditEvent.objects.filter(
            type_evenement=PlatformAuditEvent.Type.LOGIN,
            created_at__date=today,
        ).count(),
        "incidents_ouverts": SupportTicket.objects.exclude(
            statut__in=[
                SupportTicket.Statut.RESOLU,
                SupportTicket.Statut.FERME,
            ]
        ).count(),
        "stockage_sauvegardes": BackupRecord.objects.aggregate(
            total=Sum("taille_octets")
        )["total"]
        or 0,
        "revenu_30_jours": PaiementAbonnement.objects.filter(
            statut=PaiementAbonnement.Statut.VALIDE,
            date_paiement__gte=last_30_days,
        ).aggregate(total=Sum("montant"))["total"]
        or 0,
    }


def organisation_usage(organisation):
    abonnement = getattr(organisation, "abonnement", None)
    plan = abonnement.plan if abonnement else None
    utilisateurs = organisation.membres.filter(is_active=True).count()
    participants = Participant.objects.filter(organisation=organisation).count()
    formations = Formation.objects.filter(
        organisation=organisation,
        statut=Formation.Statut.ACTIVE,
    ).count()
    stockage = organisation.sauvegardes.aggregate(
        total=Sum("taille_octets")
    )["total"] or 0
    return {
        "utilisateurs": utilisateurs,
        "participants": participants,
        "formations": formations,
        "stockage_octets": stockage,
        "quota_utilisateurs": plan.max_utilisateurs if plan else 0,
        "quota_participants": plan.max_participants if plan else 0,
        "quota_formations": plan.max_formations_actives if plan else 0,
        "quota_stockage_mo": plan.max_stockage_mo if plan else 0,
    }


def live_system_health():
    started = perf_counter()
    database_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        database_ok = False
    database_latency_ms = round((perf_counter() - started) * 1000)

    cpu_percent = Decimal("0")
    ram_percent = Decimal("0")
    try:
        import psutil

        cpu_percent = Decimal(str(psutil.cpu_percent(interval=None)))
        ram_percent = Decimal(str(psutil.virtual_memory().percent))
    except ImportError:
        pass

    disk = shutil.disk_usage(".")
    disk_percent = Decimal(str(round((disk.used / disk.total) * 100, 2)))
    latest = SystemMetric.objects.first()
    return {
        "cpu_percent": cpu_percent,
        "ram_percent": ram_percent,
        "disk_percent": disk_percent,
        "database_ok": database_ok,
        "database_latency_ms": database_latency_ms,
        "redis_ok": latest.redis_ok if latest else None,
        "workers_ok": latest.workers_ok if latest else None,
        "response_time_ms": latest.response_time_ms if latest else 0,
        "errors_500": latest.errors_500 if latest else 0,
        "queue_depth": latest.queue_depth if latest else 0,
        "latest_metric": latest,
    }


def analytics_data():
    organisations_monthly = list(
        Organisation.objects.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )
    revenue_by_plan = list(
        PaiementAbonnement.objects.filter(
            statut=PaiementAbonnement.Statut.VALIDE
        )
        .values("abonnement__plan__nom")
        .annotate(total=Sum("montant"))
        .order_by("-total")
    )
    return {
        "organisations_monthly": organisations_monthly,
        "revenue_by_plan": revenue_by_plan,
    }


def _unique_organisation_slug(name):
    base = slugify(name) or "entreprise"
    candidate = base
    suffix = 2
    while Organisation.objects.filter(slug=candidate).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _unique_owner_username(organisation_slug):
    base = f"{organisation_slug[:24].upper()}-ADMIN"
    candidate = base
    suffix = 2
    user_model = get_user_model()
    while user_model.objects.filter(username__iexact=candidate).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _payment_reference(reference=""):
    if reference:
        return reference
    while True:
        candidate = f"SUB-{timezone.localdate():%Y%m%d}-{uuid4().hex[:8].upper()}"
        if not PaiementAbonnement.objects.filter(reference=candidate).exists():
            return candidate


def _cycle_duration(cycle):
    if cycle == Abonnement.Cycle.ANNUEL:
        return timedelta(days=365)
    return timedelta(days=30)


def _plan_price(plan, cycle):
    if cycle == Abonnement.Cycle.ANNUEL:
        return plan.prix_annuel
    return plan.prix_mensuel


def _create_validated_payment(
    *,
    abonnement,
    amount,
    mode,
    paid_at,
    reference="",
    actor=None,
    notes="",
    period_start=None,
    period_end=None,
):
    return PaiementAbonnement.objects.create(
        abonnement=abonnement,
        reference=_payment_reference(reference),
        montant=amount,
        mode_paiement=mode,
        statut=PaiementAbonnement.Statut.VALIDE,
        date_paiement=paid_at,
        donnees_prestataire={
            "manual": True,
            "received_by": actor.get_username() if actor else "",
            "notes": notes,
            "period_start": period_start.isoformat() if period_start else "",
            "period_end": period_end.isoformat() if period_end else "",
        },
    )


@transaction.atomic
def create_platform_organisation(cleaned_data, *, actor):
    slug = _unique_organisation_slug(cleaned_data["organisation_nom"])
    activation = cleaned_data["activation"]
    is_paid = activation == "PAYE"
    organisation = Organisation.objects.create(
        nom=cleaned_data["organisation_nom"],
        slug=slug,
        logo=cleaned_data.get("logo"),
        email=cleaned_data["organisation_email"],
        telephone=cleaned_data["organisation_telephone"],
        adresse=cleaned_data.get("adresse", ""),
        ville=cleaned_data.get("ville", ""),
        pays=cleaned_data.get("pays") or "Mali",
        statut=(
            Organisation.Statut.ACTIVE if is_paid else Organisation.Statut.ESSAI
        ),
        is_active=True,
    )

    username = (
        cleaned_data.get("owner_matricule")
        or _unique_owner_username(organisation.slug)
    )
    temporary_password = cleaned_data.get("owner_password") or (
        f"St-{get_random_string(12)}"
    )
    owner = get_user_model().objects.create_user(
        username=username,
        email=cleaned_data["owner_email"],
        password=temporary_password,
        first_name=cleaned_data["owner_first_name"],
        last_name=cleaned_data["owner_last_name"],
        telephone=cleaned_data.get("owner_telephone", ""),
        role="ADMIN",
        must_change_password=True,
    )
    MembreOrganisation.objects.create(
        organisation=organisation,
        user=owner,
        role=MembreOrganisation.Role.PROPRIETAIRE,
        invited_by=actor,
    )

    now = timezone.now()
    plan = cleaned_data["plan"]
    cycle = cleaned_data["cycle"]
    if is_paid:
        period_end = now + _cycle_duration(cycle)
        subscription_status = Abonnement.Statut.ACTIF
    else:
        period_end = now + timedelta(days=cleaned_data.get("jours_essai") or 14)
        subscription_status = Abonnement.Statut.ESSAI
        organisation.date_fin_essai = period_end
        organisation.save(update_fields=["date_fin_essai", "updated_at"])

    abonnement = Abonnement.objects.create(
        organisation=organisation,
        plan=plan,
        cycle=cycle,
        statut=subscription_status,
        date_debut=now,
        date_fin=period_end,
        montant=_plan_price(plan, cycle),
    )
    payment = None
    if is_paid:
        payment = _create_validated_payment(
            abonnement=abonnement,
            amount=cleaned_data["montant_paye"],
            mode=cleaned_data["mode_paiement"],
            paid_at=now,
            reference=cleaned_data.get("reference_paiement", ""),
            actor=actor,
            notes=cleaned_data.get("notes", ""),
            period_start=now,
            period_end=period_end,
        )
    return organisation, owner, temporary_password, abonnement, payment


@transaction.atomic
def renew_subscription_manually(abonnement, cleaned_data, *, actor):
    abonnement = Abonnement.objects.select_for_update().get(pk=abonnement.pk)
    paid_at = cleaned_data["date_paiement"]
    plan = cleaned_data["plan"]
    cycle = cleaned_data["cycle"]
    period_start = max(abonnement.date_fin, paid_at)
    period_end = period_start + _cycle_duration(cycle)

    abonnement.plan = plan
    abonnement.cycle = cycle
    abonnement.statut = Abonnement.Statut.ACTIF
    abonnement.date_debut = period_start
    abonnement.date_fin = period_end
    abonnement.montant = _plan_price(plan, cycle)
    abonnement.save(
        update_fields=[
            "plan",
            "cycle",
            "statut",
            "date_debut",
            "date_fin",
            "montant",
            "updated_at",
        ]
    )

    organisation = abonnement.organisation
    organisation.statut = Organisation.Statut.ACTIVE
    organisation.is_active = True
    organisation.date_fin_essai = None
    organisation.save(
        update_fields=["statut", "is_active", "date_fin_essai", "updated_at"]
    )

    payment = _create_validated_payment(
        abonnement=abonnement,
        amount=cleaned_data["montant"],
        mode=cleaned_data["mode_paiement"],
        paid_at=paid_at,
        reference=cleaned_data.get("reference", ""),
        actor=actor,
        notes=cleaned_data.get("notes", ""),
        period_start=period_start,
        period_end=period_end,
    )
    return abonnement, payment

