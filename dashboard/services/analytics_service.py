"""Services d'analyses du cockpit Formix."""

from __future__ import annotations


def build_analytics_metrics(raw_stats: dict) -> dict:
    analysis = raw_stats.get("analysis", {})

    return {
        "direction": analysis.get("direction", []),
        "production": analysis.get("production", []),
        "pipeline": analysis.get("pipeline", []),
        "agenda": analysis.get("agenda", []),
        "ca_series": analysis.get("ca_series", []),
        "inscription_evolution": analysis.get("inscription_evolution", []),
        "revenue_by_mode": analysis.get("revenue_by_mode", []),
    }
