"""Tests for dashboard services."""

from django.test import SimpleTestCase

from dashboard.widgets.engine import get_dashboard_widget_board


class DashboardWidgetFormattingTest(SimpleTestCase):
    def test_money_widgets_use_compact_values_to_avoid_overflow(self):
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

        self.assertEqual(values["ca_jour"], "15 k FCFA")
        self.assertEqual(values["ca_mois"], "1.2 M FCFA")
        self.assertEqual(values["ca_annee"], "1.2 Md FCFA")
