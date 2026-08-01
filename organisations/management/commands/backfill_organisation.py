from django.apps import apps
from django.core.management.base import BaseCommand

from organisations.models import Organisation

OWNED_MODELS = [
    ("dashboard", "ConfigurationOrganisation"),
    ("formations", "CategorieFormation"),
    ("formations", "Formation"),
    ("formations", "SessionFormation"),
    ("formations", "Seance"),
    ("participants", "Participant"),
    ("participants", "DocumentParticipant"),
    ("inscriptions", "Inscription"),
    ("inscriptions", "HistoriqueStatutInscription"),
    ("paiements", "Paiement"),
    ("paiements", "Remboursement"),
    ("presences", "Presence"),
    ("documents", "Attestation"),
    ("documents", "DocumentGenere"),
    ("core", "AuditLog"),
    ("rh", "Department"),
    ("rh", "Position"),
    ("rh", "Employee"),
    ("rh", "EmployeeHistory"),
    ("rh", "EmployeeAuditLog"),
    ("comptes", "Compte"),
    ("comptabilite_ohada", "ConfigurationComptable"),
    ("comptabilite_ohada", "ExerciceComptable"),
    ("comptabilite_ohada", "EcritureComptable"),
    ("comptabilite_ohada", "Immobilisation"),
    ("comptabilite_ohada", "ReleveBancaire"),
]

PAYROLL_ENTERPRISE_MODELS = [
    ("django_paie", "EcheanceSalariale"),
    ("django_paie", "PeriodePaie"),
    ("django_paie", "VariablePaieMensuelle"),
    ("django_paie", "ReglePaie"),
]


class Command(BaseCommand):
    help = "Attribue les anciennes donnees metier a une organisation."

    def add_arguments(self, parser):
        parser.add_argument("--slug", required=True)

    def handle(self, *args, **options):
        organisation = Organisation.objects.get(slug=options["slug"])
        total = 0

        for app_label, model_name in OWNED_MODELS:
            model = apps.get_model(app_label, model_name)
            updated = model.objects.filter(organisation__isnull=True).update(
                organisation=organisation
            )
            total += updated
            self.stdout.write(f"{app_label}.{model_name}: {updated}")

        payroll_total = 0
        for app_label, model_name in PAYROLL_ENTERPRISE_MODELS:
            model = apps.get_model(app_label, model_name)
            updated = model.objects.filter(entreprise_id="").update(
                entreprise_id=organisation.slug
            )
            payroll_total += updated
            self.stdout.write(f"{app_label}.{model_name}.entreprise_id: {updated}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill termine: {total} objet(s) rattache(s) a {organisation}; "
                f"{payroll_total} objet(s) paie calibres sur {organisation.slug}."
            )
        )
