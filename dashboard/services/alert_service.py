"""Services d'alertes du cockpit Formix."""

from __future__ import annotations


def build_alerts(raw_stats: dict) -> list[dict]:
    alerts = list(raw_stats.get("alerts", []))
    return [
        {
            "level": alert.get("level", "info"),
            "icon": alert.get("icon", "\u26a0"),
            "text": alert.get("text", ""),
        }
        for alert in alerts
    ]
