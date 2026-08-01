from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError

from comptes.models import Compte
from organisations.models import Organisation
from paiements.models import Paiement
from paiements.services.mouvement_sync_service import ensure_payment_movement


class Command(BaseCommand):
    help = (
        "Audite et synchronise les mouvements financiers manquants pour les "
        "paiements de formation valides."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--organisation-slug",
            dest="organisation_slug",
            help="Limiter la synchronisation a une organisation.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Afficher ce qui serait corrige sans creer de mouvement.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        organisation_slug = options.get("organisation_slug")

        payments = Paiement.objects.select_related(
            "organisation",
            "compte",
            "enregistre_par",
            "inscription",
        ).filter(
            statut=Paiement.Statut.VALIDE,
            compte__isnull=False,
        )

        if organisation_slug:
            organisation = Organisation.objects.filter(slug=organisation_slug).first()
            if not organisation:
                self.stderr.write(self.style.ERROR("Organisation introuvable."))
                return
            payments = payments.filter(organisation=organisation)

        checked = created = linked = skipped = 0
        impacted_accounts: set[int] = set()

        try:
            for payment in payments.order_by("date_paiement", "id"):
                checked += 1
                if dry_run:
                    result = ensure_payment_movement_preview(payment)
                else:
                    with transaction.atomic():
                        result = ensure_payment_movement(payment)

                if result.created:
                    created += 1
                    if not dry_run:
                        impacted_accounts.add(payment.compte_id)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{'A creer' if dry_run else 'Mouvement cree'} pour {payment.numero_recu} "
                            f"({payment.montant:,.0f} {payment.compte.devise})"
                        )
                    )
                elif result.linked:
                    linked += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"{'A rattacher' if dry_run else 'Ancien mouvement rattache'} a {payment.numero_recu}"
                        )
                    )
                elif result.skipped_reason:
                    skipped += 1
        except (OperationalError, ProgrammingError) as exc:
            raise CommandError(
                "Impossible de lire les paiements. Verifie que les migrations "
                "sont appliquees avant la synchronisation: python manage.py migrate"
            ) from exc

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Synthese"))
        self.stdout.write(f"Paiements verifies : {checked}")
        self.stdout.write(f"Mouvements crees : {created}")
        self.stdout.write(f"Mouvements rattaches : {linked}")
        self.stdout.write(f"Paiements ignores : {skipped}")
        self.stdout.write(
            "Mode : dry-run, aucune ecriture"
            if dry_run
            else "Mode : ecriture, synchronisation appliquee"
        )

        if impacted_accounts:
            accounts = Compte.objects.filter(pk__in=impacted_accounts).order_by("code")
            self.stdout.write("")
            self.stdout.write("Comptes impactes :")
            for account in accounts:
                self.stdout.write(
                    f"- {account.code} | {account.nom} | "
                    f"solde actuel {account.solde_actuel:,.0f} {account.devise}"
                )


def ensure_payment_movement_preview(payment):
    from paiements.services.mouvement_sync_service import (
        PaymentMovementSyncResult,
        find_unlinked_payment_movement,
        get_payment_movement,
    )

    if payment.statut != Paiement.Statut.VALIDE:
        return PaymentMovementSyncResult(None, skipped_reason="paiement_non_valide")
    if not payment.compte_id:
        return PaymentMovementSyncResult(None, skipped_reason="compte_absent")
    existing = get_payment_movement(payment)
    if existing:
        return PaymentMovementSyncResult(existing)
    unlinked = find_unlinked_payment_movement(payment)
    if unlinked:
        return PaymentMovementSyncResult(unlinked, linked=True)
    return PaymentMovementSyncResult(None, created=True)
