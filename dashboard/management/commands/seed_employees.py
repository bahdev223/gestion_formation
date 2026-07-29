from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from django_rh.models import Department, Employee, Position
from django_paie.services import ModeSimpleService


class Command(BaseCommand):
    help = "Crée un jeu de démonstration RH réaliste pour BALY'S GROUP."

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
        ("BLY-EMP-001", "Mamadou", "Baly", "M", date(1985, 3, 12), "+224 622 10 10 01", "mamadou.baly@balysgroup.com", "DIR", "DG", "CDI", 3500000, "active", date(2021, 1, 4)),
        ("BLY-EMP-002", "Aïssatou", "Camara", "F", date(1990, 7, 22), "+224 622 10 10 02", "aissatou.camara@balysgroup.com", "ADM", "RAF", "CDI", 2200000, "active", date(2022, 2, 1)),
        ("BLY-EMP-003", "Ibrahima", "Diallo", "M", date(1992, 11, 8), "+224 622 10 10 03", "ibrahima.diallo@balysgroup.com", "ADM", "COMPTA", "CDI", 1450000, "active", date(2022, 6, 13)),
        ("BLY-EMP-004", "Fatoumata", "Bah", "F", date(1989, 5, 17), "+224 622 10 10 04", "fatoumata.bah@balysgroup.com", "FORM", "RESP-FORM", "CDI", 2100000, "active", date(2021, 9, 6)),
        ("BLY-EMP-005", "Moussa", "Condé", "M", date(1991, 1, 25), "+224 622 10 10 05", "moussa.conde@balysgroup.com", "FORM", "FORMATEUR", "CDD", 1250000, "active", date(2024, 1, 15)),
        ("BLY-EMP-006", "Mariama", "Sylla", "F", date(1995, 9, 3), "+224 622 10 10 06", "mariama.sylla@balysgroup.com", "FORM", "FORMATEUR", "consultant", 1100000, "active", date(2024, 4, 2)),
        ("BLY-EMP-007", "Abdoulaye", "Keita", "M", date(1993, 6, 14), "+224 622 10 10 07", "abdoulaye.keita@balysgroup.com", "COM", "COMMERCIAL", "CDI", 1300000, "active", date(2023, 3, 20)),
        ("BLY-EMP-008", "Hawa", "Soumah", "F", date(1997, 12, 1), "+224 622 10 10 08", "hawa.soumah@balysgroup.com", "COM", "COMMUNITY", "CDD", 950000, "active", date(2025, 2, 10)),
        ("BLY-EMP-009", "Ousmane", "Touré", "M", date(1988, 4, 19), "+224 622 10 10 09", "ousmane.toure@balysgroup.com", "OPS", "COORDO", "CDI", 1700000, "active", date(2022, 10, 3)),
        ("BLY-EMP-010", "Nènè", "Kourouma", "F", date(1998, 8, 27), "+224 622 10 10 10", "nene.kourouma@balysgroup.com", "ADM", "ASSIST", "CDD", 850000, "recruited", None),
        ("BLY-EMP-011", "Alpha", "Sow", "M", date(1994, 2, 9), "+224 622 10 10 11", "alpha.sow@balysgroup.com", "RH", "RESP-RH", "CDI", 1800000, "active", date(2023, 7, 3)),
        ("BLY-EMP-012", "Kadiatou", "Bangoura", "F", date(1999, 10, 30), "+224 622 10 10 12", "kadiatou.bangoura@balysgroup.com", "FORM", "FORMATEUR", "internship", 500000, "recruited", None),
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
