"""Services participants du cockpit Formix."""

from __future__ import annotations


def build_participant_metrics(raw_stats: dict) -> dict:
    participants = raw_stats.get("participants", {})
    analysis = raw_stats.get("analysis", {})

    return {
        "cards": [
            ("today", "Nouveaux aujourd'hui", participants.get("today", 0)),
            ("week", "Cette semaine", participants.get("week", 0)),
            ("month", "Ce mois", participants.get("month", 0)),
            ("year", "Cette ann\u00e9e", participants.get("year", 0)),
            ("actifs", "Actifs", participants.get("actifs", 0)),
            ("en_attente", "En attente", participants.get("en_attente", 0)),
            ("termines", "Termin\u00e9s", participants.get("termines", 0)),
            ("abandons", "Abandons", participants.get("abandons", 0)),
            ("taux_reussite", "Taux de r\u00e9ussite", participants.get("taux_reussite", 0)),
            ("taux_presence", "Taux de pr\u00e9sence", participants.get("taux_presence", 0)),
        ],
        "pipeline": participants.get("pipeline", []),
        "gender": participants.get("gender", []),
        "age_distribution": participants.get("age_distribution", []),
        "top_entreprises": participants.get("top_entreprises", []),
        "city": participants.get("city", []),
        "inscription_evolution": analysis.get("inscription_evolution", []),
    }
