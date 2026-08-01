"""Tests for dashboard services."""

from django.test import SimpleTestCase

from dashboard.services.dashboard_service import _with_percent
from dashboard.widgets.engine import get_dashboard_widget_board


class DashboardWidgetFormattingTest(SimpleTestCase):
    def test_money_widgets_keep_full_values_for_business_readability(self):
        board = get_dashboard_widget_board(
            profile="directeur",
            active_tab="finance",
            stats={
                "finance": {
                    "ca_jour": 15_000,
                    "ca_mois": 1_250_000,
                    "ca_annee": 1_200_000_000,
                }
            },
        )

        values = {widget.key: widget.value for widget in board["active"]}

        self.assertEqual(values["ca_jour"], "15,000 FCFA")
        self.assertEqual(values["ca_mois"], "1,250,000 FCFA")
        self.assertEqual(values["ca_annee"], "1,200,000,000 FCFA")

    def test_chart_items_include_percentages_for_visual_bars(self):
        rows = _with_percent(
            [
                {"label": "Formation A", "value": 100},
                {"label": "Formation B", "value": 50},
            ]
        )

        self.assertEqual(rows[0]["percent"], 100)
        self.assertEqual(rows[1]["percent"], 50)
