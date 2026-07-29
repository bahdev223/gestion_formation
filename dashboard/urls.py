from django.urls import path

from .views import ConfigurationOrganisationView, dashboard_home
from .payroll_views import (
    payroll_employee_salary_update,
    payroll_employees,
    payroll_generate,
)
from .rh_views import (
    DepartmentCreateView,
    DepartmentListView,
    rh_dashboard,
    rh_employee_create,
)

app_name = "dashboard"

urlpatterns = [
    path("", dashboard_home, name="home"),
    path("dashboard/", dashboard_home, name="index"),
    path(
        "paie-salariale/employes/",
        payroll_employees,
        name="payroll-employees",
    ),
    path(
        "ressources-humaines/dashboard/",
        rh_dashboard,
        name="rh-dashboard",
    ),
    path(
        "ressources-humaines/employes/create/",
        rh_employee_create,
        name="rh-employee-create",
    ),
    path(
        "ressources-humaines/departements/",
        DepartmentListView.as_view(),
        name="rh-department-list",
    ),
    path(
        "ressources-humaines/departements/create/",
        DepartmentCreateView.as_view(),
        name="rh-department-create",
    ),
    path(
        "paie-salariale/employes/<int:user_id>/salaire/",
        payroll_employee_salary_update,
        name="payroll-employee-salary-update",
    ),
    path(
        "paie-salariale/generer/",
        payroll_generate,
        name="payroll-generate",
    ),
    path(
        "parametres-entreprise/",
        ConfigurationOrganisationView.as_view(),
        name="organisation-settings",
    ),
]
