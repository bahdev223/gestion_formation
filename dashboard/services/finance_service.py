"""Services financiers du cockpit Formix (couche métier dédiée)."""

from __future__ import annotations


def build_finance_metrics(raw_stats: dict) -> dict:
    finance = raw_stats.get("finance", {})

    return {
        "cards": [
            ("ca_jour", "Recettes du jour", finance.get("ca_jour", 0)),
            ("ca_semaine", "Recettes semaine", finance.get("ca_semaine", 0)),
            ("ca_mois", "Recettes mois", finance.get("ca_mois", 0)),
            ("ca_annee", "Recettes ann\u00e9e", finance.get("ca_annee", 0)),
            ("encaissements", "Encaissements", finance.get("encaissements", 0)),
            ("decaissements", "D\u00e9caissements", finance.get("decaissements", 0)),
            ("reste_a_encaisser", "Reste \u00e0 encaisser", finance.get("reste_a_encaisser", 0)),
            ("factures_impayees", "Factures impay\u00e9es", finance.get("factures_impayees", 0)),
        ],
        "treasury": {
            "total": finance.get("treasury", 0),
            "bank": finance.get("bank", 0),
            "cash": finance.get("cash", 0),
            "orange_money": finance.get("orange_money", 0),
            "wave": finance.get("wave", 0),
            "moov_money": finance.get("moov_money", 0),
        },
        "modes": finance.get("modes", []),
    }
