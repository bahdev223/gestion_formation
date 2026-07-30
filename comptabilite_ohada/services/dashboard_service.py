from datetime import timedelta
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from ..models import EcritureComptable, ExerciceComptable, LigneEcritureComptable


class DashboardService:
    """Agrégation des données pour le tableau de bord comptable."""

    def __init__(self, organisation):
        # organisation est obligatoire : un repli sur None produisait des
        # statistiques comptables consolidant toutes les organisations.
        if organisation is None:
            raise ValueError(
                "DashboardService exige une organisation : sans elle, les "
                "agregats melangeraient les donnees de tous les clients."
            )
        self.organisation = organisation

    def _ecritures(self):
        return EcritureComptable.objects.filter(organisation=self.organisation)

    def _exercices(self):
        return ExerciceComptable.objects.filter(organisation=self.organisation)

    def _lignes(self):
        return LigneEcritureComptable.objects.select_related(
            "ecriture", "compte"
        ).filter(ecriture__organisation=self.organisation)

    def synthese(self, exercice=None):
        if exercice is None:
            exercice = self._exercices().filter(cloture=False).first()

        base = self._lignes().filter(ecriture__validee=True)
        if exercice:
            base = base.filter(
                ecriture__date_ecriture__gte=exercice.date_debut,
                ecriture__date_ecriture__lte=exercice.date_fin,
            )

        total_debit = base.aggregate(t=Sum("debit"))["t"] or Decimal("0.00")
        total_credit = base.aggregate(t=Sum("credit"))["t"] or Decimal("0.00")

        tresorerie = base.filter(
            Q(compte__code__startswith="57")
            | Q(compte__code__startswith="52")
            | Q(compte__code__startswith="581")
        ).aggregate(debit=Sum("debit"), credit=Sum("credit"))
        solde_tresorerie = (tresorerie["debit"] or Decimal("0.00")) - (
            tresorerie["credit"] or Decimal("0.00")
        )

        charges = (
            base.filter(compte__code__startswith="6").aggregate(t=Sum("debit"))["t"]
            or Decimal("0.00")
        )
        produits = (
            base.filter(compte__code__startswith="7").aggregate(t=Sum("credit"))["t"]
            or Decimal("0.00")
        )

        nb_ecritures = self._ecritures().filter(validee=True)
        if exercice:
            nb_ecritures = nb_ecritures.filter(exercice=exercice)

        return {
            "total_debit": total_debit,
            "total_credit": total_credit,
            "solde_tresorerie": solde_tresorerie,
            "total_charges": charges,
            "total_produits": produits,
            "resultat": produits - charges,
            "nb_ecritures": nb_ecritures.count(),
            "exercice": exercice,
        }

    def evolution_tresorerie(self, jours=30):
        depuis = timezone.now().date() - timedelta(days=jours)
        lignes = (
            self._lignes()
            .filter(ecriture__validee=True, ecriture__date_ecriture__gte=depuis)
            .filter(
                Q(compte__code__startswith="57")
                | Q(compte__code__startswith="52")
                | Q(compte__code__startswith="581")
            )
            .values("ecriture__date_ecriture")
            .annotate(debit=Sum("debit"), credit=Sum("credit"))
            .order_by("ecriture__date_ecriture")
        )

        return [
            {
                "date": item["ecriture__date_ecriture"],
                "debit": item["debit"],
                "credit": item["credit"],
            }
            for item in lignes
        ]

    def alertes(self):
        alerts = []
        try:
            from ..models import ConfigurationComptable

            config = ConfigurationComptable.objects.filter(
                organisation=self.organisation
            ).first()
        except Exception:
            return alerts

        if config and not config.est_initialise:
            alerts.append(
                {
                    "niveau": "warning",
                    "message": "Le plan comptable n'est pas encore initialisé",
                }
            )

        nb_brouillon = self._ecritures().filter(validee=False).count()
        if nb_brouillon > 0:
            alerts.append(
                {
                    "niveau": "info",
                    "message": f"{nb_brouillon} écriture(s) en brouillon à valider",
                }
            )

        return alerts

    def compter_ecritures(self):
        return self._ecritures().count()

    def compter_ecritures_non_validees(self):
        return self._ecritures().filter(validee=False).count()

    def dernieres_ecritures(self, limit=10):
        return self._ecritures().select_related("journal", "exercice").order_by(
            "-date_ecriture", "-created_at"
        )[:limit]

    def exercice_courant(self):
        exercice = self._exercices().filter(cloture=False).first()
        return str(exercice) if exercice else None

    def totaux_par_journal(self):
        return (
            self._ecritures()
            .values("journal__code")
            .annotate(total=Sum("lignes__debit"))
            .order_by("journal__code")
        )
