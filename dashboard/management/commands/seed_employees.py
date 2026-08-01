from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from django_paie.services import ModeSimpleService
from django_rh.models import Department, Employee, Position


class Command(BaseCommand):
    help = "Crée un jeu de démonstration RH générique."

    departments = [
        ("DIR", "Direction générale", "Pilotage stratégique et gouvernance."),
        ("ADM", "Administration & Finance", "Administration, finance et comptabilité."),
        ("FORM", "Formation", "Conception et animation des programmes de formation."),
        ("COM", "Commercial & Marketing", "Développement commercial et communication."),
        ("OPS", "Opérations", "Logistique et coordination opérationnelle."),
        ("RH", "Ressources humaines", "Gestion du personnel et développement RH."),
    ]

    positions = [
        ("DG", "Directeur général", "DIR"),
        ("RAF", "Responsable administratif et financier", "ADM"),
        ("COMPTA", "Comptable", "ADM"),
        ("RESP-FORM", "Responsable des formations", "FORM"),
        ("FORMATEUR", "Formateur", "FORM"),
        ("COMMERCIAL", "Chargé commercial", "COM"),
        ("COMMUNITY", "Community manager", "COM"),
        ("COORDO", "Coordinateur des opérations", "OPS"),
        ("ASSIST", "Assistant administratif", "ADM"),
        ("RESP-RH", "Responsable RH", "RH"),
    ]

    employees = [
        ("DEMO-EMP-001", "Mamadou", "Keita", "M", date(1985, 3, 12), "+223 70 00 00 01", "mamadou.keita@example.test", "DIR", "DG", "CDI", 3500000, "active", date(2021, 1, 4)),
        ("DEMO-EMP-002", "Aïssatou", "Camara", "F", date(1990, 7, 22), "+223 70 00 00 02", "aissatou.camara@example.test", "ADM", "RAF", "CDI", 2200000, "active", date(2022, 2, 1)),
        ("DEMO-EMP-003", "Ibrahima", "Diallo", "M", date(1992, 11, 8), "+223 70 00 00 03", "ibrahima.diallo@example.test", "ADM", "COMPTA", "CDI", 1450000, "active", date(2022, 6, 13)),
        ("DEMO-EMP-004", "Fatoumata", "Bah", "F", date(1989, 5, 17), "+223 70 00 00 04", "fatoumata.bah@example.test", "FORM", "RESP-FORM", "CDI", 2100000, "active", date(2021, 9, 6)),
        ("DEMO-EMP-005", "Moussa", "Condé", "M", date(1991, 1, 25), "+223 70 00 00 05", "moussa.conde@example.test", "FORM", "FORMATEUR", "CDD", 1250000, "active", date(2024, 1, 15)),
        ("DEMO-EMP-006", "Mariama", "Sylla", "F", date(1995, 9, 3), "+223 70 00 00 06", "mariama.sylla@example.test", "FORM", "FORMATEUR", "consultant", 1100000, "active", date(2024, 4, 2)),
        ("DEMO-EMP-007", "Abdoulaye", "Keita", "M", date(1993, 6, 14), "+223 70 00 00 07", "abdoulaye.keita@example.test", "COM", "COMMERCIAL", "CDI", 1300000, "active", date(2023, 3, 20)),
        ("DEMO-EMP-008", "Hawa", "Soumah", "F", date(1997, 12, 1), "+223 70 00 00 08", "hawa.soumah@example.test", "COM", "COMMUNITY", "CDD", 950000, "active", date(2025, 2, 10)),
        ("DEMO-EMP-009", "Ousmane", "Touré", "M", date(1988, 4, 19), "+223 70 00 00 09", "ousmane.toure@example.test", "OPS", "COORDO", "CDI", 1700000, "active", date(2022, 10, 3)),
        ("DEMO-EMP-010", "Nènè", "Kourouma", "F", date(1998, 8, 27), "+223 70 00 00 10", "nene.kourouma@example.test", "ADM", "ASSIST", "CDD", 850000, "recruited", None),
        ("DEMO-EMP-011", "Alpha", "Sow", "M", date(1994, 2, 9), "+223 70 00 00 11", "alpha.sow@example.test", "RH", "RESP-RH", "CDI", 1800000, "active", date(2023, 7, 3)),
        ("DEMO-EMP-012", "Kadiatou", "Bangoura", "F", date(1999, 10, 30), "+223 70 00 00 12", "kadiatou.bangoura@example.test", "FORM", "FORMATEUR", "internship", 500000, "recruited", None),
    ]

    @transaction.atomic
    def handle(self, *args, **options):
        departments = {}
        for code, name, description in self.departments:
            department, _ = Department.objects.update_or_create(
                code=code,
                defaults={"name": name, "description": description},
            )
            departments[code] = department

        positions = {}
        for code, title, department_code in self.positions:
            position, _ = Position.objects.update_or_create(
                code=code,
                defaults={
                    "title": title,
                    "department": departments[department_code],
                },
            )
            positions[code] = position

        creator = get_user_model().objects.filter(is_superuser=True).first()
        created = 0
        updated = 0
        seeded = {}
        for item in self.employees:
            (
                matricule, first_name, last_name, sex, birth_date, phone, email,
                department_code, position_code, contract_type, salary, status,
                hire_date,
            ) = item
            employee, was_created = Employee.objects.update_or_create(
                matricule=matricule,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "sex": sex,
                    "birth_date": birth_date,
                    "phone": phone,
                    "email": email,
                    "department": departments[department_code],
                    "position": positions[position_code],
                    "contract_type": contract_type,
                    "salaire_mensuel": Decimal(salary),
                    "status": status,
                    "hire_date": hire_date,
                    "created_by": creator,
                },
            )
            seeded[matricule] = employee
            created += int(was_created)
            updated += int(not was_created)

        manager_map = {
            "DIR": "BLY-EMP-001",
            "ADM": "BLY-EMP-002",
            "FORM": "BLY-EMP-004",
            "COM": "BLY-EMP-007",
            "OPS": "BLY-EMP-009",
            "RH": "BLY-EMP-011",
        }
        for department_code, matricule in manager_map.items():
            department = departments[department_code]
            department.manager = seeded[matricule]
            department.save(update_fields=["manager"])

        payroll_service = ModeSimpleService()
        payroll_periods = ("06/2026", "07/2026")
        payroll_count = 0
        active_employees = Employee.objects.filter(
            matricule__in=seeded,
            status=Employee.Status.ACTIVE,
            salaire_mensuel__isnull=False,
            salaire_mensuel__gt=0,
        )
        for period in payroll_periods:
            for employee in active_employees:
                payroll_service.creer_echeance(
                    employee,
                    period,
                    employee.salaire_mensuel,
                )
                payroll_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed RH terminé : {created} employés créés, "
                f"{updated} mis à jour, {len(departments)} départements "
                f"et {len(positions)} postes. {payroll_count} échéances "
                f"salariales disponibles pour juin et juillet 2026."
            )
        )
