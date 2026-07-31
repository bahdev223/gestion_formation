"""Services analytiques du tableau de bord entreprise.

Centralise le calcul des indicateurs. Les templates ne contiennent que la
présentation.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import TypedDict

from django.db import models
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from accounts.models import User
from comptes.models import Compte, MouvementCompte
from dashboard.services import (
    alert_service,
    analytics_service,
    finance_service,
    formation_service,
    operation_service,
    participant_service,
)
from dashboard.widgets.engine import get_dashboard_widget_board
from django_rh.models import Employee
from documents.models import Attestation, DocumentGenere
from formations.models import Formation, Seance, SessionFormation
from inscriptions.models import Inscription
from organisations.models import MembreOrganisation, Organisation
from paiements.models import Paiement
from participants.models import Participant
from presences.models import Presence


class _Event(TypedDict):
    at: str
    title: str
    detail: str
    category: str
    amount: Decimal
    href: str


def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _safe_pct(numerator: Decimal, denominator: Decimal) -> Decimal:
    den = _to_decimal(denominator)
    if den <= 0:
        return Decimal("0")
    return (_to_decimal(numerator) * Decimal("100")) / den


def _safe_delta(current: Decimal, previous: Decimal) -> Decimal:
    prev = _to_decimal(previous)
    if prev <= 0:
        return Decimal("0")
    return ((_to_decimal(current) - prev) / prev) * Decimal("100")


def _first_day_of_month(today: date) -> date:
    return today.replace(day=1)


def _first_day_of_next_month(today: date) -> date:
    if today.month == 12:
        return date(today.year + 1, 1, 1)
    return date(today.year, today.month + 1, 1)


def _shift_month(month_start: date, step: int) -> date:
    total = (month_start.month - 1) + step
    year = month_start.year + total // 12
    month = total % 12 + 1
    return date(year, month, 1)


def _resolve_profile(request) -> str:
    member = getattr(request, "organisation_member", None)
    if getattr(request.user, "is_superuser", False):
        return "directeur"
    if member is None:
        role = getattr(request.user, "role", "")
        if role == User.Role.ADMIN:
            return "directeur"
        if role == User.Role.FORMATEUR:
            return "formateur"
        if role == User.Role.COMPTABLE:
            return "comptable"
        return "responsable"
    if member.role == MembreOrganisation.Role.PROPRIETAIRE:
        return "directeur"
    if member.role == MembreOrganisation.Role.ADMIN:
        return "directeur"
    if member.role == MembreOrganisation.Role.RESPONSABLE:
        return "responsable"
    if member.role == MembreOrganisation.Role.FORMATEUR:
        return "formateur"
    if member.role == MembreOrganisation.Role.COMPTABLE:
        return "comptable"
    return "responsable"


def _tabs_for_profile(profile: str) -> list[dict[str, str]]:
    base = [
        {"key": "vision", "label": "Vue générale"},
        {"key": "finance", "label": "Finances"},
        {"key": "formations", "label": "Formations"},
        {"key": "participants", "label": "Participants"},
        {"key": "rh", "label": "RH"},
        {"key": "comptabilite", "label": "Comptabilité"},
        {"key": "operations", "label": "Opérations"},
        {"key": "analyses", "label": "Analyses"},
    ]
    if profile == "formateur":
        return [
            {"key": "vision", "label": "Vue générale"},
            {"key": "formations", "label": "Mes sessions"},
            {"key": "participants", "label": "Mes apprenants"},
            {"key": "operations", "label": "Actions"},
            {"key": "analyses", "label": "Mes objectifs"},
        ]
    if profile == "comptable":
        return [
            {"key": "vision", "label": "Vue générale"},
            {"key": "finance", "label": "Finances"},
            {"key": "comptabilite", "label": "Comptabilité"},
            {"key": "operations", "label": "Opérations"},
            {"key": "analyses", "label": "Pilotage"},
        ]
    return base


def _age_distribution(participants_qs):
    data = defaultdict(int)
    today = timezone.localdate()
    for participant in participants_qs.exclude(date_naissance__isnull=True):
        age = today.year - participant.date_naissance.year
        if (today.month, today.day) < (participant.date_naissance.month, participant.date_naissance.day):
            age -= 1
        if age < 20:
            data["<20"] += 1
        elif age < 30:
            data["20-29"] += 1
        elif age < 40:
            data["30-39"] += 1
        elif age < 50:
            data["40-49"] += 1
        elif age < 60:
            data["50-59"] += 1
        else:
            data["60+"] += 1
    return [
        {"label": "moins de 20 ans", "value": data["<20"]},
        {"label": "20 à 29 ans", "value": data["20-29"]},
        {"label": "30 à 39 ans", "value": data["30-39"]},
        {"label": "40 à 49 ans", "value": data["40-49"]},
        {"label": "50 à 59 ans", "value": data["50-59"]},
        {"label": "60 ans et +", "value": data["60+"]},
    ]


def _month_series(organisation, today: date, months: int = 6):
    start = _first_day_of_month(today)
    valid_payments = Paiement.objects.filter(organisation=organisation, statut=Paiement.Statut.VALIDE)
    result = []
    max_total = Decimal("1")
    for step in range(months - 1, -1, -1):
        month_start = _shift_month(start, -step)
        month_end = _first_day_of_next_month(month_start)
        total = _to_decimal(
            valid_payments.filter(
                date_paiement__date__gte=month_start,
                date_paiement__date__lt=month_end,
            ).aggregate(
                total=Coalesce(Sum("montant"), Decimal("0"), output_field=models.DecimalField())
            )["total"]
        )
        result.append({
            "label": month_start.strftime("%b"),
            "month": month_start.strftime("%Y-%m"),
            "value": total,
        })
        if total > max_total:
            max_total = total
    for item in result:
        item["height"] = int(_safe_pct(item["value"], max_total))
    return result


def _cash_sources(organisation):
    accounts = Compte.objects.filter(organisation=organisation, actif=True)
    bank = _to_decimal(accounts.filter(type=Compte.TypeCompte.BANQUE).aggregate(
        total=Coalesce(Sum("solde_actuel"), Decimal("0"), output_field=models.DecimalField())
    )["total"])
    cash = _to_decimal(accounts.filter(type=Compte.TypeCompte.ESPECES).aggregate(
        total=Coalesce(Sum("solde_actuel"), Decimal("0"), output_field=models.DecimalField())
    )["total"])
    mobile = _to_decimal(accounts.filter(type=Compte.TypeCompte.MOBILE_MONEY).aggregate(
        total=Coalesce(Sum("solde_actuel"), Decimal("0"), output_field=models.DecimalField())
    )["total"])

    wave = _to_decimal(accounts.filter(
        type__in=[Compte.TypeCompte.MOBILE_MONEY, Compte.TypeCompte.PORTEFEUILLE_NUMERIQUE],
        nom__icontains="wave",
    ).aggregate(total=Coalesce(Sum("solde_actuel"), Decimal("0"), output_field=models.DecimalField())["total"]))
    moov = _to_decimal(accounts.filter(
        type__in=[Compte.TypeCompte.MOBILE_MONEY, Compte.TypeCompte.PORTEFEUILLE_NUMERIQUE],
        nom__icontains="moov",
    ).aggregate(total=Coalesce(Sum("solde_actuel"), Decimal("0"), output_field=models.DecimalField())["total"]))
    orange = mobile - wave - moov

    return {
        "banque": bank,
        "caisse": cash,
        "orange_money": orange,
        "wave": wave,
        "moov_money": moov,
        "total": _to_decimal(accounts.aggregate(
            total=Coalesce(Sum("solde_actuel"), Decimal("0"), output_field=models.DecimalField())
        )["total"]),
    }


def _build_operations_feed(organisation, active_inscriptions, valid_payments, today: date):
    events: list[_Event] = []
    for ins in active_inscriptions.select_related("participant", "session", "session__formation").order_by("-created_at")[:4]:
        events.append({
            "at": ins.created_at.isoformat(),
            "title": "Nouvelle inscription",
            "detail": f"{ins.participant.nom_complet} — {ins.session.titre}",
            "category": "inscription",
            "amount": _to_decimal(ins.montant_final),
            "href": "/inscriptions/",
        })
    for payment in valid_payments.select_related("inscription__participant").order_by("-date_paiement")[:4]:
        events.append({
            "at": payment.date_paiement.isoformat(),
            "title": "Paiement reçu",
            "detail": f"{payment.inscription.participant.nom_complet} — {payment.montant:,.0f} FCFA",
            "category": "paiement",
            "amount": _to_decimal(payment.montant),
            "href": "/paiements/",
        })
    for att in Attestation.objects.filter(organisation=organisation).order_by("-created_at")[:2]:
        events.append({
            "at": att.created_at.isoformat(),
            "title": "Attestation générée",
            "detail": f"{att.nom_participant} ({att.titre_session})",
            "category": "document",
            "amount": Decimal("0"),
            "href": "/documents/",
        })
    for doc in DocumentGenere.objects.filter(organisation=organisation).order_by("-created_at")[:2]:
        events.append({
            "at": doc.created_at.isoformat(),
            "title": "Document exporté",
            "detail": doc.get_type_document_display(),
            "category": "document",
            "amount": Decimal("0"),
            "href": "/documents/",
        })
    events.sort(key=lambda item: item["at"], reverse=True)
    if not events:
        events.append({
            "at": today.isoformat(),
            "title": "Plateforme active",
            "detail": "Aucune activité récente.",
            "category": "systeme",
            "amount": Decimal("0"),
            "href": "/",
        })
    return events[:12]


def get_dashboard_statistics(filters=None):
    if filters is None:
        filters = {}
    request = filters.get("request")
    organisation: Organisation | None = filters.get("organisation")
    if request is not None and organisation is None:
        organisation = getattr(request, "organisation", None)
    if organisation is None:
        return {"error": "Organisation indisponible"}

    today = timezone.localdate()
    profile = _resolve_profile(request)
    tabs = _tabs_for_profile(profile)
    active_tab = request.GET.get("tab") if request is not None else None
    if not active_tab or active_tab not in {tab["key"] for tab in tabs}:
        active_tab = tabs[0]["key"]

    week_start = today - timedelta(days=today.weekday())
    month_start = _first_day_of_month(today)
    next_month_start = _first_day_of_next_month(today)
    last_month_start = _shift_month(month_start, -1)
    year_start = today.replace(month=1, day=1)
    next_year_start = date(today.year + 1, 1, 1)

    payments_qs = Paiement.objects.filter(organisation=organisation)
    inscriptions_qs = Inscription.objects.filter(organisation=organisation)
    sessions_qs = SessionFormation.objects.filter(organisation=organisation)
    formations_qs = Formation.objects.filter(organisation=organisation)
    participants_qs = Participant.objects.filter(organisation=organisation)
    presence_qs = Presence.objects.filter(organisation=organisation)
    active_inscriptions = inscriptions_qs.exclude(statut=Inscription.Statut.ANNULE)
    valid_payments = payments_qs.filter(statut=Paiement.Statut.VALIDE)

    # Finances
    facturation = _to_decimal(active_inscriptions.aggregate(
        total=Coalesce(Sum("montant_final"), Decimal("0"), output_field=models.DecimalField())
    )["total"])
    encaisse = _to_decimal(valid_payments.aggregate(
        total=Coalesce(Sum("montant"), Decimal("0"), output_field=models.DecimalField())
    )["total"])
    reste_global = max(facturation - encaisse, Decimal("0"))
    ca_jour = _to_decimal(valid_payments.filter(date_paiement__date=today).aggregate(
        total=Coalesce(Sum("montant"), Decimal("0"), output_field=models.DecimalField())
    )["total"])
    ca_semaine = _to_decimal(valid_payments.filter(
        date_paiement__date__gte=week_start,
        date_paiement__date__lt=week_start + timedelta(days=7),
    ).aggregate(
        total=Coalesce(Sum("montant"), Decimal("0"), output_field=models.DecimalField())
    )["total"])
    ca_mois = _to_decimal(valid_payments.filter(
        date_paiement__date__gte=month_start,
        date_paiement__date__lt=next_month_start,
    ).aggregate(
        total=Coalesce(Sum("montant"), Decimal("0"), output_field=models.DecimalField())
    )["total"])
    ca_mois_dernier = _to_decimal(valid_payments.filter(
        date_paiement__date__gte=last_month_start,
        date_paiement__date__lt=month_start,
    ).aggregate(
        total=Coalesce(Sum("montant"), Decimal("0"), output_field=models.DecimalField())
    )["total"])
    ca_annee = _to_decimal(valid_payments.filter(
        date_paiement__date__gte=year_start,
        date_paiement__date__lt=next_year_start,
    ).aggregate(
        total=Coalesce(Sum("montant"), Decimal("0"), output_field=models.DecimalField())
    )["total"])

    today_moves = MouvementCompte.objects.filter(
        compte__organisation=organisation,
        statut=MouvementCompte.StatutMouvement.VALIDE,
        annule=False,
        date__date=today,
    )
    encaisse_jour = _to_decimal(today_moves.filter(
        sens=MouvementCompte.SensMouvement.ENTREE,
    ).aggregate(total=Coalesce(Sum("montant"), Decimal("0"), output_field=models.DecimalField())["total"])
    )
    decaisse_jour = _to_decimal(today_moves.filter(
        sens=MouvementCompte.SensMouvement.SORTIE,
    ).aggregate(total=Coalesce(Sum("montant"), Decimal("0"), output_field=models.DecimalField())["total"])
    )

    sources = _cash_sources(organisation)
    low_accounts = list(
        Compte.objects.filter(organisation=organisation, actif=True, solde_actuel__lt=0).order_by("solde_actuel")[:6]
    )

    # Inscriptions / impayés
    unpaid = active_inscriptions.exclude(statut_paiement__in=[Inscription.StatutPaiement.PAYE, Inscription.StatutPaiement.TROP_PERCU])
    impayes = unpaid.count()
    montants_attendus = Decimal("0")
    for inscription in unpaid:
        deja_paye = _to_decimal(
            inscription.paiements.filter(statut=Paiement.Statut.VALIDE).aggregate(
                total=Coalesce(Sum("montant"), Decimal("0"), output_field=models.DecimalField())
            )["total"]
        )
        montants_attendus += max(_to_decimal(inscription.montant_final) - deja_paye, Decimal("0"))
    retards = unpaid.filter(statut=Inscription.Statut.EN_COURS).count()

    mode_distribution = []
    for row in valid_payments.values("mode_paiement").annotate(total=Coalesce(
        Sum("montant"),
        Decimal("0"),
        output_field=models.DecimalField(),
    )).order_by("-total"):
        mode_distribution.append({
            "label": Paiement.ModePaiement(row["mode_paiement"]).label if row["mode_paiement"] in dict(Paiement.ModePaiement.choices) else row["mode_paiement"],
            "value": _to_decimal(row["total"]),
        })

    # Top débiteurs
    top_unpaid = []
    for ins in unpaid.order_by("-montant_final")[:5]:
        paye = _to_decimal(
            ins.paiements.filter(statut=Paiement.Statut.VALIDE).aggregate(
                total=Coalesce(Sum("montant"), Decimal("0"), output_field=models.DecimalField())
            )["total"]
        )
        reste = max(_to_decimal(ins.montant_final) - paye, Decimal("0"))
        top_unpaid.append({
            "participant": ins.participant.nom_complet,
            "montant": reste,
        })

    # Formations
    sessions_open = sessions_qs.filter(
        statut__in=[
            SessionFormation.Statut.PLANIFIEE,
            SessionFormation.Statut.INSCRIPTIONS_OUVERTES,
            SessionFormation.Statut.EN_COURS,
        ]
    ).count()
    sessions_complete = sessions_qs.filter(
        statut__in=[SessionFormation.Statut.COMPLETE, SessionFormation.Statut.TERMINEE]
    ).count()
    sessions_cancelled = sessions_qs.filter(statut=SessionFormation.Statut.ANNULEE).count()
    sessions_upcoming = sessions_qs.filter(
        date_debut__gte=today,
    ).exclude(statut=SessionFormation.Statut.ANNULEE)

    session_stats_qs = sessions_qs.filter(
        ~Q(statut=SessionFormation.Statut.ANNULEE),
        capacite_max__gt=0,
    ).annotate(
        enrolled=Count("inscriptions", filter=~Q(inscriptions__statut=Inscription.Statut.ANNULE))
    ).values("capacite_max", "enrolled")
    capacity_total = Decimal(sum(item["capacite_max"] for item in session_stats_qs))
    capacity_used = Decimal(sum(min(item["enrolled"], item["capacite_max"]) for item in session_stats_qs))
    taux_remplissage = _safe_pct(capacity_used, capacity_total)

    formation_plus_rentable = (
        formations_qs.annotate(
            revenue=Coalesce(Sum("sessions__inscriptions__paiements__montant", filter=Q(sessions__inscriptions__paiements__statut=Paiement.Statut.VALIDE), output_field=models.DecimalField()), Decimal("0"))
        )
        .order_by("-revenue")
        .first()
    )
    formation_moins_rentable = (
        formations_qs.annotate(
            revenue=Coalesce(Sum("sessions__inscriptions__paiements__montant", filter=Q(sessions__inscriptions__paiements__statut=Paiement.Statut.VALIDE), output_field=models.DecimalField()), Decimal("0"))
        )
        .order_by("revenue")
        .first()
    )
    formation_plus_demandee = (
        formations_qs.annotate(
            demande=Count("sessions__inscriptions", filter=~Q(sessions__inscriptions__statut=Inscription.Statut.ANNULE))
        )
        .order_by("-demande")
        .first()
    )
    top_formation_revenus = list(
        formations_qs.annotate(
            revenue=Coalesce(
                Sum("sessions__inscriptions__paiements__montant", filter=Q(sessions__inscriptions__paiements__statut=Paiement.Statut.VALIDE), output_field=models.DecimalField()),
                Decimal("0"),
            )
        )
        .order_by("-revenue")
        .values("nom", "revenue")[:5]
    )

    # Participants
    participant_today = participants_qs.filter(created_at__date=today).count()
    participant_week = participants_qs.filter(created_at__date__gte=week_start).count()
    participant_month = participants_qs.filter(
        created_at__date__gte=month_start,
        created_at__date__lt=next_month_start,
    ).count()
    participant_previous_month = participants_qs.filter(
        created_at__date__gte=last_month_start,
        created_at__date__lt=month_start,
    ).count()
    participant_year = participants_qs.filter(created_at__date__gte=year_start, created_at__date__lt=next_year_start).count()
    status_count = active_inscriptions.values("statut").annotate(total=Count("id"))
    status_map = {row["statut"]: row["total"] for row in status_count}
    termines = status_map.get(Inscription.Statut.TERMINE, 0)
    abandons = status_map.get(Inscription.Statut.ABANDONNE, 0)
    succès_base = _to_decimal(termines)
    succès_total = _to_decimal(termines + abandons + status_map.get(Inscription.Statut.CONFIRME, 0) + status_map.get(Inscription.Statut.EN_COURS, 0))
    taux_reussite = _safe_pct(succès_base, succès_total)
    present = presence_qs.filter(statut__in=[Presence.Statut.PRESENT, Presence.Statut.RETARD]).count()
    total_presence = presence_qs.count()
    taux_presence = _safe_pct(_to_decimal(present), _to_decimal(total_presence))
    top_entreprises = list(
        participants_qs.exclude(entreprise="")
        .values("entreprise")
        .annotate(total=Count("id"))
        .order_by("-total")[:6]
    )
    top_villes = list(
        participants_qs.exclude(ville="")
        .values("ville")
        .annotate(total=Count("id"))
        .order_by("-total")[:6]
    )

    # RH / formateurs
    employes_actifs = Employee.objects.filter(
        organisation=organisation,
        status=Employee.Status.ACTIVE,
    ).count()
    employes_conges = Employee.objects.filter(
        organisation=organisation, status=Employee.Status.TERMINATED
    ).count()
    membres_formateurs = MembreOrganisation.objects.filter(
        organisation=organisation, role=MembreOrganisation.Role.FORMATEUR, is_active=True
    )
    formateurs_total = membres_formateurs.count()
    formateurs_occupes = sessions_qs.filter(statut=SessionFormation.Statut.EN_COURS).values("formateur_id").distinct().count()
    top_formateur = membres_formateurs.select_related("user").order_by("user__username").first()
    if top_formateur is not None:
        top_formateur_nom = top_formateur.user.get_full_name() or top_formateur.user.username
    else:
        top_formateur_nom = "—"

    # alertes
    alerts = []
    impayes_alert = impayes
    if impayes_alert > 0:
        alerts.append({"level": "danger", "icon": "⚠", "text": f"{impayes_alert} paiements impayés"})
    tomorrow_count = sessions_upcoming.filter(date_debut=today + timedelta(days=1)).count()
    if tomorrow_count > 0:
        alerts.append({"level": "info", "icon": "🔔", "text": f"{tomorrow_count} formation(s) démarre(nt) demain"})
    if len(low_accounts) > 0:
        alerts.append({"level": "warning", "icon": "⚠", "text": f"{len(low_accounts)} compte(s) de trésorerie en solde faible"})
    echeance_aujourd_hui = 0
    if organisation.date_fin_essai:
        jours = (organisation.date_fin_essai.date() - today).days
        if jours <= 10 and jours >= 0:
            alerts.append({"level": "warning", "icon": "⏳", "text": f"Essai expire dans {jours} jours"})

    operations = _build_operations_feed(organisation, active_inscriptions, valid_payments, today)

    # Agenda + analyses
    agenda = []
    for session in sessions_qs.filter(date_debut__gte=today, date_debut__lte=today + timedelta(days=14)).order_by("date_debut")[:8]:
        agenda.append({
            "date": session.date_debut.isoformat(),
            "type": "Formation",
            "title": f"{session.titre} — {session.formation.nom}",
            "href": f"/o/{organisation.slug}/formations/sessions/{session.pk}/",
        })

    analysis = {
        "ca_series": _month_series(organisation=organisation, today=today, months=6),
        "inscription_evolution": [
            {"label": "Aujourd'hui", "value": participant_today},
            {"label": "Semaine", "value": participant_week},
            {"label": "Mois", "value": participant_month},
            {"label": "Année", "value": participant_year},
        ],
        "revenue_by_mode": mode_distribution,
        "pipeline": [
            {"name": "Pré-inscrits", "value": status_map.get(Inscription.Statut.PREINSCRIT, 0)},
            {"name": "Confirmés", "value": status_map.get(Inscription.Statut.CONFIRME, 0)},
            {"name": "En formation", "value": status_map.get(Inscription.Statut.EN_COURS, 0)},
            {"name": "Terminés", "value": termines},
        ],
        "agenda": agenda,
        "direction": [
            {"label": "CA", "value": ca_mois, "delta": _safe_delta(ca_mois, ca_mois_dernier)},
            {"label": "Bénéfice", "value": encaisse - decaisse_jour, "delta": _safe_delta(ca_mois - decaisse_jour, ca_mois_dernier)},
            {"label": "Participants", "value": participant_month, "delta": _safe_delta(_to_decimal(participant_month), _to_decimal(participant_previous_month))},
            {"label": "Impayés", "value": impayes, "delta": Decimal("0")},
            {"label": "Présence", "value": taux_presence, "delta": Decimal("0")},
            {"label": "Satisfaction", "value": Decimal("0"), "delta": Decimal("0")},
        ],
        "production": [
            {"label": "Taux de remplissage", "value": taux_remplissage},
            {"label": "Sessions actives", "value": sessions_open},
            {"label": "Taux paiement", "value": _safe_pct(encaisse, facturation)},
        ],
        "top_formation_revenus": [
            {"label": item["nom"], "value": _to_decimal(item["revenue"])} for item in top_formation_revenus
        ],
    }

    return {
        "dashboard_tabs": tabs,
        "active_tab": active_tab,
        "role": profile,
        "title": "Centre de pilotage d’entreprise",
        "subtitle": "Vue d’ensemble des activités",
        "general": {
            "ca_mois": ca_mois,
            "benefice": encaisse - decaisse_jour,
            "treasury": sources["total"],
            "formations_en_cours": sessions_open,
            "taux_remplissage": taux_remplissage,
            "taux_paiement": _safe_pct(encaisse, facturation),
            "satisfaction": "—",
            "alertes": len(alerts),
        },
        "finance": {
            "ca_jour": ca_jour,
            "ca_semaine": ca_semaine,
            "ca_mois": ca_mois,
            "ca_annee": ca_annee,
            "encaissements": encaisse,
            "decaissements": decaisse_jour,
            "benefice": encaisse - decaisse_jour,
            "reste_a_encaisser": reste_global,
            "montants_attendus": montants_attendus,
            "factures_impayees": impayes,
            "retards": retards,
            "echeances_jour": echeance_aujourd_hui,
            "treasury": sources["total"],
            "bank": sources["banque"],
            "cash": sources["caisse"],
            "orange_money": sources["orange_money"],
            "wave": sources["wave"],
            "moov_money": sources["moov_money"],
            "encaisse_jour": encaisse_jour,
            "decaisse_jour": decaisse_jour,
            "modes": mode_distribution,
            "low_accounts_count": len(low_accounts),
        },
        "formations": {
            "total": formations_qs.count(),
            "actives": formations_qs.filter(statut=Formation.Statut.ACTIVE).count(),
            "terminees": formations_qs.filter(statut=Formation.Statut.ARCHIVEE).count(),
            "sessions_ouvertes": sessions_open,
            "sessions_complete": sessions_complete,
            "sessions_annulees": sessions_cancelled,
            "sessions_a_venir": sessions_upcoming.count(),
            "taux_remplissage": taux_remplissage,
            "formation_plus_rentable": formation_plus_rentable.nom if formation_plus_rentable else "—",
            "formation_moins_rentable": formation_moins_rentable.nom if formation_moins_rentable else "—",
            "formation_plus_demandee": formation_plus_demandee.nom if formation_plus_demandee else "—",
            "heures_formation": Seance.objects.filter(session__organisation=organisation).count(),
            "next_formations": list(sessions_upcoming.order_by("date_debut")[:5]),
        },
        "participants": {
            "today": participant_today,
            "week": participant_week,
            "month": participant_month,
            "year": participant_year,
            "actifs": participants_qs.filter(statut=Participant.Statut.ACTIF).count(),
            "en_attente": participants_qs.filter(statut=Participant.Statut.INACTIF).count(),
            "termines": termines,
            "abandons": abandons,
            "taux_reussite": taux_reussite,
            "taux_presence": taux_presence,
            "gender": [
                {"label": "Homme", "value": participants_qs.filter(genre=Participant.Genre.HOMME).count()},
                {"label": "Femme", "value": participants_qs.filter(genre=Participant.Genre.FEMME).count()},
                {"label": "Autre", "value": participants_qs.filter(genre=Participant.Genre.AUTRE).count()},
            ],
            "age_distribution": _age_distribution(participants_qs),
            "city": top_villes,
            "top_entreprises": top_entreprises,
            "pipeline": [
                {"name": "Pré-inscrits", "value": status_map.get(Inscription.Statut.PREINSCRIT, 0)},
                {"name": "Confirmés", "value": status_map.get(Inscription.Statut.CONFIRME, 0)},
                {"name": "En formation", "value": status_map.get(Inscription.Statut.EN_COURS, 0)},
                {"name": "Terminés", "value": termines},
            ],
        },
        "paiements": {
            "recu_aujourd_hui": ca_jour,
            "montants_attendus": montants_attendus,
            "retards": retards,
            "impayes": impayes,
            "top_debiteurs": top_unpaid,
            "paiements_a_venir": status_map.get(Inscription.Statut.CONFIRME, 0) + status_map.get(Inscription.Statut.PREINSCRIT, 0),
            "echeances_jour": echeance_aujourd_hui,
            "modes": mode_distribution,
            "mouvements": operations[:4],
        },
        "formateurs": {
            "total": formateurs_total,
            "disponibles": max(formateurs_total - formateurs_occupes, 0),
            "occupes": formateurs_occupes,
            "absents": 0,
            "heures": Seance.objects.filter(session__organisation=organisation).count(),
            "sessions": sessions_qs.count(),
            "eval": Decimal("0"),
            "revenu": ca_mois,
            "top_formateur": top_formateur_nom,
        },
        "rh": {
            "employes_actifs": employes_actifs,
            "present": employes_actifs,
            "absents": 0,
            "retards": 0,
            "conges": employes_conges,
            "top_formateur": top_formateur_nom,
        },
        "comptabilite": {
            "balance": sources["total"],
            "balance_by_source": sources,
            "mouvements_critiques": [{"label": compte.code, "solde": compte.solde_actuel} for compte in low_accounts],
        },
        "operations": {
            "timeline": operations,
            "agenda": agenda,
            "agenda_prod": [
                {"label": "Salles", "value": 0},
                {"label": "Formateurs", "value": _safe_pct(formateurs_occupes, max(formateurs_total, 1))},
                {"label": "Équipements", "value": Decimal("0")},
            ],
        },
        "alerts": alerts,
        "analysis": analysis,
    }

    stats["widget_board"] = get_dashboard_widget_board(
        profile=profile,
        active_tab=active_tab,
        stats=stats,
    )
    stats["finance_metrics"] = finance_service.build_finance_metrics(stats)
    stats["formation_metrics"] = formation_service.build_formation_metrics(stats)
    stats["participant_metrics"] = participant_service.build_participant_metrics(stats)
    stats["operation_metrics"] = operation_service.build_operation_metrics(stats)
    stats["analytics_metrics"] = analytics_service.build_analytics_metrics(stats)
    stats["alert_cards"] = alert_service.build_alerts(stats)

    return stats
