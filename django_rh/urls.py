from django.urls import path
from django_rh.api import (
    create_employee, list_employees, get_employee,
    hire_employee, terminate_employee, suspend_employee,
    list_departments, create_department,
    list_positions, create_position,
    dashboard_stats,
)

app_name = "rh"

urlpatterns = [
    path("api/employees/", list_employees, name="employee-list"),
    path("api/employees/create/", create_employee, name="employee-create"),
    path("api/employees/<int:employee_id>/", get_employee, name="employee-detail"),
    path("api/employees/<int:employee_id>/hire/", hire_employee, name="employee-hire"),
    path("api/employees/<int:employee_id>/suspend/", suspend_employee, name="employee-suspend"),
    path("api/employees/<int:employee_id>/terminate/", terminate_employee, name="employee-terminate"),
    path("api/departments/", list_departments, name="department-list"),
    path("api/departments/create/", create_department, name="department-create"),
    path("api/positions/", list_positions, name="position-list"),
    path("api/positions/create/", create_position, name="position-create"),
    path("api/dashboard/stats/", dashboard_stats, name="dashboard-stats"),
]
