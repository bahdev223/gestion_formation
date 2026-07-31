"""Selectors du tableau de bord entreprise."""

from dashboard.services.dashboard_service import get_dashboard_statistics as _compute_statistics


def get_dashboard_statistics(filters=None):
    """Délègue à la couche service métier (logique calculs).

    Garder un selector léger permet d'encapsuler la logique d'orchestration.
    """
    return _compute_statistics(filters or {})
