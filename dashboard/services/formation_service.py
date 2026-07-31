"""Services formation du cockpit Formix."""

from __future__ import annotations


def build_formation_metrics(raw_stats: dict) -> dict:
    formations = raw_stats.get("formations", {})
    analysis = raw_stats.get("analysis", {})

    return {
        "cards": [
            ("total", "Formations", formations.get("total", 0)),
            ("sessions_ouvertes", "Sessions ouvertes", formations.get("sessions_ouvertes", 0)),
            ("sessions_complete", "Sessions compl\u00e8tes", formations.get("sessions_complete", 0)),
            ("sessions_annulees", "Sessions annul\u00e9es", formations.get("sessions_annulees", 0)),
            ("sessions_a_venir", "Sessions \u00e0 venir", formations.get("sessions_a_venir", 0)),
            ("taux_remplissage", "Taux de remplissage", formations.get("taux_remplissage", 0)),
            ("formation_plus_rentable", "Formation la plus rentable", formations.get("formation_plus_rentable", "\u2014")),
            ("formation_plus_demandee", "Plus demand\u00e9e", formations.get("formation_plus_demandee", "\u2014")),
            ("heures_formation", "Heures r\u00e9alis\u00e9es", formations.get("heures_formation", 0)),
        ],
        "top_revenus": analysis.get("top_formation_revenus", []),
        "production_pipeline": analysis.get("production", []),
    }
