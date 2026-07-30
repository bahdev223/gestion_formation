from django.db.models import Count
from django_rh.models import Employee, Department


class EmployeeQueries:
    def employees_by_department(self) -> list[dict]:
        return list(
            Department.objects.annotate(count=Count("employee"))
            .values("id", "code", "name", "count")
            .order_by("-count")
        )

    def employees_by_status(self) -> list[dict]:
        return list(
            Employee.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )

    def employees_by_contract_type(self) -> list[dict]:
        return list(
            Employee.objects.values("contract_type")
            .annotate(count=Count("id"))
            .order_by("contract_type")
        )
