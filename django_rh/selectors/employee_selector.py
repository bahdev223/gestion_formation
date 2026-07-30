from django.db.models import QuerySet
from django_rh.models import Employee, Department, Position


class EmployeeSelector:
    def get_by_id(self, employee_id: int) -> Employee | None:
        try:
            return Employee.objects.select_related("department", "position", "created_by").get(id=employee_id)
        except Employee.DoesNotExist:
            return None

    def list_employees(self, status: str | None = None, department_id: int | None = None) -> QuerySet[Employee]:
        qs = Employee.objects.select_related("department", "position").all()
        if status:
            qs = qs.filter(status=status)
        if department_id:
            qs = qs.filter(department_id=department_id)
        return qs.order_by("-created_at")

    def list_departments(self) -> QuerySet[Department]:
        return Department.objects.all().order_by("name")

    def list_positions(self) -> QuerySet[Position]:
        return Position.objects.all().order_by("title")

    def get_dashboard_stats(self) -> dict:
        from django.db.models import Count
        return {
            "total_employees": Employee.objects.count(),
            "active_count": Employee.objects.filter(status="active").count(),
            "suspended_count": Employee.objects.filter(status="suspended").count(),
            "terminated_count": Employee.objects.filter(status="terminated").count(),
            "department_count": Department.objects.count(),
            "position_count": Position.objects.count(),
        }
