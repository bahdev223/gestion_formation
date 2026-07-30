from django_rh.models import Employee


def generate_matricule(prefix: str = "EMP") -> str:
    last = Employee.objects.filter(matricule__startswith=prefix).order_by("-id").first()
    num = int(last.matricule.split("-")[1]) + 1 if last else 1
    return f"{prefix}-{num:06d}"
