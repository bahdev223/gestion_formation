from django.db.models import QuerySet

from django_rh.models import Department, Employee, Position


class EmployeeSelector:
    """Lectures RH, isolees par organisation.

    organisation est obligatoire sur toutes les methodes : ces selectors
    alimentaient des listes et des statistiques sans aucun filtre tenant,
    exposant les employes, departements et postes de tous les clients.
    """

    def __init__(self, organisation=None):
        self.organisation = organisation

    def _organisation(self, organisation=None):
        value = organisation or self.organisation
        if value is None:
            raise ValueError(
                "EmployeeSelector exige une organisation : sans elle, les "
                "listes RH melangeraient les donnees de tous les clients."
            )
        return value

    def get_by_id(self, employee_id: int, organisation=None) -> Employee | None:
        try:
            return Employee.objects.select_related(
                "department", "position", "created_by"
            ).get(
                id=employee_id, organisation=self._organisation(organisation)
            )
        except Employee.DoesNotExist:
            return None

    def list_employees(
        self,
        status: str | None = None,
        department_id: int | None = None,
        organisation=None,
    ) -> QuerySet[Employee]:
        qs = Employee.objects.select_related("department", "position").filter(
            organisation=self._organisation(organisation)
        )
        if status:
            qs = qs.filter(status=status)
        if department_id:
            qs = qs.filter(department_id=department_id)
        return qs.order_by("-created_at")

    def list_departments(self, organisation=None) -> QuerySet[Department]:
        return Department.objects.filter(
            organisation=self._organisation(organisation)
        ).order_by("name")

    def list_positions(self, organisation=None) -> QuerySet[Position]:
        return Position.objects.filter(
            organisation=self._organisation(organisation)
        ).order_by("title")

    def get_dashboard_stats(self, organisation=None) -> dict:
        organisation = self._organisation(organisation)
        employees = Employee.objects.filter(organisation=organisation)
        return {
            "total_employees": employees.count(),
            "active_count": employees.filter(status="active").count(),
            "suspended_count": employees.filter(status="suspended").count(),
            "terminated_count": employees.filter(status="terminated").count(),
            "department_count": Department.objects.filter(
                organisation=organisation
            ).count(),
            "position_count": Position.objects.filter(
                organisation=organisation
            ).count(),
        }
