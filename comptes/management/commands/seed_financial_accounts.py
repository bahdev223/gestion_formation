from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from comptes.models import Compte


class Command(BaseCommand):
    help = "Crée les comptes financiers de base de l'organisation sélectionnée."

    accounts = [
        {
            "code": "CAISSE-01",
            "nom": "Caisse principale",
            "type": "ESPECES",
            "role": "PRINCIPAL",
            "compte_comptable_code": "571",
        },
        {
            "code": "BANQUE-01",
            "nom": "Compte bancaire principal",
            "type": "BANQUE",
            "role": "PRINCIPAL",
            "compte_comptable_code": "521",
        },
        {
            "code": "OM-01",
            "nom": "Orange Money",
            "type": "MOBILE_MONEY",
            "role": "ENCAISSEMENT",
            "compte_comptable_code": "521",
        },
        {
            "code": "MTN-01",
            "nom": "MTN Mobile Money",
            "type": "MOBILE_MONEY",
            "role": "ENCAISSEMENT",
            "compte_comptable_code": "521",
        },
        {
            "code": "DEP-01",
            "nom": "Caisse des décaissements",
            "type": "ESPECES",
            "role": "DECAISSEMENT",
            "compte_comptable_code": "571",
        },
    ]

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        updated = 0
        for data in self.accounts:
            _, was_created = Compte.objects.update_or_create(
                code=data["code"],
                defaults={
                    **data,
                    "devise": "XOF",
                    "taux_change": Decimal("1"),
                    "devise_reference": "XOF",
                    "actif": True,
                },
            )
            created += int(was_created)
            updated += int(not was_created)
        self.stdout.write(
            self.style.SUCCESS(
                f"Comptes financiers : {created} créés, {updated} mis à jour."
            )
        )
