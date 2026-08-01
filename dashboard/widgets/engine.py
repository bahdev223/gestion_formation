"""Moteur de widgets du tableau de bord.

Structure réutilisable pour créer un cockpit orienté opérationnel métier.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class DashboardWidget:
    key: str
    title: str
    value: Any
    hint: str = ""
    icon: str = "\u25cf"
    tone: str = "primary"
    href: str = ""
    kind: str = "card"
    detail: str = ""


def _card(tab: str, key: str, title: str, value: Any, hint: str, icon: str, tone: str = "primary") -> DashboardWidget:
    return DashboardWidget(
        key=key,
        title=title,
        value=value,
        hint=hint,
        icon=icon,
        tone=tone,
    )


def _build_cards(
    profile: str,
    general: dict[str, Any],
    finance: dict[str, Any],
    formations: dict[str, Any],
    participants: dict[str, Any],
    rh: dict[str, Any],
    comptabilite: dict[str, Any],
    operations: dict[str, Any],
    analysis: dict[str, Any],
) -> dict[str, list[DashboardWidget]]:
    """Construit des widgets par onglet.

    Les valeurs sont formatées ici pour rester strictement présentables (pas de SQL ici).
    """

    def _pc(val: Any) -> str:
        try:
            return f"{float(val):.1f}%"
        except (TypeError, ValueError):
            return "0.0%"

    def _money(val: Any) -> str:
        try:
            amount = float(val)
        except (TypeError, ValueError):
            return "0 FCFA"
        abs_amount = abs(amount)
        if abs_amount >= 1_000_000_000:
            return f"{amount / 1_000_000_000:.1f} Md FCFA".replace(".0 ", " ")
        if abs_amount >= 1_000_000:
            return f"{amount / 1_000_000:.1f} M FCFA".replace(".0 ", " ")
        if abs_amount >= 10_000:
            return f"{amount / 1_000:.1f} k FCFA".replace(".0 ", " ")
        return f"{amount:,.0f} FCFA"

    direction = analysis.get("direction", [])
    production = analysis.get("production", [])

    widgets_by_tab: dict[str, list[DashboardWidget]] = {
        "vision": [
            _card("vision", "ca_mois", "Chiffre d'affaires", _money(general.get("ca_mois")), "Ce mois", "[CA]", "primary"),
            _card("vision", "benefice", "B\u00e9n\u00e9fice estim\u00e9", _money(general.get("benefice")), "Encaissements - d\u00e9caissements", "[MONEY]", "success"),
            _card("vision", "treasury", "Tr\u00e9sorerie", _money(general.get("treasury")), "Disponible", "[SAFE]", "info"),
            _card("vision", "formations_en_cours", "Formations en cours", formations.get("sessions_ouvertes", 0), "Sessions actives", "[BOOKS]"),
            _card("vision", "alertes", "Alertes", general.get("alertes", 0), "Points d'action", "[ALERT]", "danger"),
            _card("vision", "taux_remplissage", "Taux de remplissage", _pc(general.get("taux_remplissage")), "Capacit\u00e9", "[FILL]", "info"),
        ],
        "finance": [
            _card("finance", "ca_jour", "Recettes du jour", _money(finance.get("ca_jour")), "Aujourd'hui", "[DAY]", "primary"),
            _card("finance", "ca_semaine", "Recettes semaine", _money(finance.get("ca_semaine")), "7 jours", "[WEEK]", "primary"),
            _card("finance", "ca_mois", "Recettes mois", _money(finance.get("ca_mois")), "Ce mois", "[MONTH]", "success"),
            _card("finance", "ca_annee", "Recettes ann\u00e9e", _money(finance.get("ca_annee")), "Depuis janvier", "[YEAR]", "primary"),
            _card("finance", "encaissements", "Encaissements", _money(finance.get("encaissements")), "Valid\u00e9s", "[IN]", "success"),
            _card("finance", "decaissements", "D\u00e9caissements", _money(finance.get("decaissements")), "Sorties", "[OUT]", "danger"),
            _card("finance", "reste_a_encaisser", "Reste \u00e0 encaisser", _money(finance.get("reste_a_encaisser")), "Facturation en attente", "[PENDING]", "warning"),
            _card("finance", "factures_impayees", "Factures impay\u00e9es", finance.get("factures_impayees", 0), "A traiter", "[UNPAID]", "danger"),
        ],
        "formations": [
            _card("formations", "formation_total", "Formations", formations.get("total", 0), "Catalogue", "[CAT]"),
            _card("formations", "sessions_open", "Sessions ouvertes", formations.get("sessions_ouvertes", 0), "Actives", "[OPEN]"),
            _card("formations", "sessions_complete", "Sessions compl\u00e8tes", formations.get("sessions_complete", 0), "Termin\u00e9es", "[DONE]", "success"),
            _card("formations", "sessions_annulees", "Sessions annul\u00e9es", formations.get("sessions_annulees", 0), "Suivi", "[CANCEL]", "warning"),
            _card("formations", "taux_remplissage", "Taux de remplissage", _pc(formations.get("taux_remplissage")), "Capacit\u00e9", "[FILL]", "info"),
            _card("formations", "heures", "Heures r\u00e9alis\u00e9es", formations.get("heures_formation", 0), "Conduites", "[TIME]"),
        ],
        "participants": [
            _card("participants", "participant_today", "Nouveaux", participants.get("today", 0), "Aujourd'hui", "[NEW]"),
            _card("participants", "participant_week", "Cette semaine", participants.get("week", 0), "7 jours", "[WEEK]"),
            _card("participants", "participant_month", "Ce mois", participants.get("month", 0), "Ce mois", "[MONTH]"),
            _card("participants", "termine", "Termin\u00e9s", participants.get("termines", 0), "Formations finies", "[DONE]"),
            _card("participants", "abandons", "Abandons", participants.get("abandons", 0), "A traiter", "[DROP]", "danger"),
            _card("participants", "taux_presence", "Taux de pr\u00e9sence", _pc(participants.get("taux_presence")), "Fr\u00e9quentation", "[ATTEND]", "info"),
            _card("participants", "taux_reussite", "Taux de r\u00e9ussite", _pc(participants.get("taux_reussite")), "Efficience", "[SUCCESS]", "success"),
        ],
        "rh": [
            _card("rh", "employes_actifs", "Employ\u00e9s actifs", rh.get("employes_actifs", 0), "En poste", "[EMP]", "primary"),
            _card("rh", "conges", "En cong\u00e9", rh.get("conges", 0), "Cong\u00e9s", "[LEAVE]", "warning"),
            _card("rh", "absents", "Absents", rh.get("absents", 0), "Aujourd'hui", "[ABS]", "danger"),
            _card("rh", "retards", "Retards", rh.get("retards", 0), "Pointage", "[LATE]", "warning"),
            _card("rh", "top_formateur", "Top formateur", rh.get("top_formateur", "\u2014"), "Performance", "[TOP]"),
        ],
        "comptabilite": [
            _card("comptabilite", "balance", "Balance consolid\u00e9e", _money(comptabilite.get("balance")), "Global", "[BAL]", "primary"),
            _card("comptabilite", "bank", "Banque", _money(finance.get("bank")), "Compte bancaire", "[BANK]", "info"),
            _card("comptabilite", "cash", "Caisse", _money(finance.get("cash")), "Liquidit\u00e9", "[CASH]", "success"),
            _card("comptabilite", "orange_money", "Orange Money", _money(finance.get("orange_money")), "Mobile", "[OM]", "warning"),
            _card("comptabilite", "moov_money", "Moov Money", _money(finance.get("moov_money")), "Mobile", "[MM]", "warning"),
            _card("comptabilite", "critical_alerts", "Alertes compta", len(comptabilite.get("mouvements_critiques", [])), "Comptes faibles", "[ALERT]", "danger"),
        ],
        "operations": [
            _card("operations", "timeline", "Activit\u00e9s r\u00e9centes", len(operations.get("timeline", [])), "12 derniers items", "[ACT]", "info"),
            _card("operations", "agenda", "Agenda", len(operations.get("agenda", [])), "14 jours", "[CAL]", "primary"),
            _card("operations", "paiements_a_venir", "Paiements \u00e0 venir", operations.get("mouvements", [])[:1] and operations.get("mouvements")[0].get("title", ""), "Prochaine action", "[TODO]", "warning"),
            _card("operations", "production_rate", "Taux de production", _pc(production[2].get("value", 0) if len(production) > 2 else 0), "Satisfaction op\u00e9rationnelle", "[RATE]", "success"),
        ],
        "analyses": [
            _card("analyses", "direction_ca", "Direction CA", direction[0].get("value", 0) if direction else 0, "Vue entreprise", "[DIR]", "primary",),
            _card("analyses", "direction_benefice", "Direction b\u00e9n\u00e9fice", direction[1].get("value", 0) if len(direction) > 1 else 0, "Sant\u00e9", "[DIR]", "success"),
            _card("analyses", "direction_participants", "Direction participants", direction[2].get("value", 0) if len(direction) > 2 else 0, "Volume", "[DIR]", "info"),
            _card("analyses", "direction_impayes", "Direction impay\u00e9s", direction[3].get("value", 0) if len(direction) > 3 else 0, "Risque", "[DIR]", "danger"),
            _card("analyses", "satisfaction", "Satisfaction", participants.get("satisfaction", 0), "Qualit\u00e9", "[NPS]"),
        ],
    }

    if profile == "formateur":
        return {
            "vision": widgets_by_tab["vision"],
            "formations": widgets_by_tab["formations"],
            "participants": widgets_by_tab["participants"],
            "operations": widgets_by_tab["operations"],
            "analyses": widgets_by_tab["analyses"],
        }
    if profile == "comptable":
        return {
            "vision": widgets_by_tab["vision"],
            "finance": widgets_by_tab["finance"],
            "comptabilite": widgets_by_tab["comptabilite"],
            "operations": widgets_by_tab["operations"],
            "analyses": widgets_by_tab["analyses"],
        }
    return widgets_by_tab


def get_dashboard_widget_board(
    profile: str,
    active_tab: str,
    stats: dict[str, Any],
) -> dict[str, Any]:
    """Retourne un objet prêt pour le template."""
    widgets_by_tab = _build_cards(
        profile=profile,
        general=stats.get("general", {}),
        finance=stats.get("finance", {}),
        formations=stats.get("formations", {}),
        participants=stats.get("participants", {}),
        rh=stats.get("rh", {}),
        comptabilite=stats.get("comptabilite", {}),
        operations=stats.get("operations", {}),
        analysis=stats.get("analysis", {}),
    )
    return {
        "all": widgets_by_tab,
        "active": widgets_by_tab.get(active_tab, []),
    }


def flatten_widgets(widgets_by_tab: dict[str, Iterable[DashboardWidget]]) -> list[DashboardWidget]:
    return [widget for row in widgets_by_tab.values() for widget in row]
