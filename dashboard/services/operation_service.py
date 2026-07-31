"""Services opérationnels du cockpit Formix."""

from __future__ import annotations


def build_operation_metrics(raw_stats: dict) -> dict:
    operations = raw_stats.get("operations", {})
    alerts = raw_stats.get("alerts", [])

    return {
        "timeline": operations.get("timeline", []),
        "agenda": operations.get("agenda", []),
        "agenda_prod": operations.get("agenda_prod", []),
        "alerts": alerts,
        "quick_actions": [
            "Nouvelle inscription",
            "Nouveau paiement",
            "G\u00e9n\u00e9rer un document",
        ],
    }
