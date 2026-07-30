import pytest
from django_rh.services import EmployeeService
from django_rh.models import Employee, EmployeeHistory, EmployeeAuditLog, Department, Position


class TestRHWorkflow:
    def test_full_employee_lifecycle(self, db):
        svc = EmployeeService()
        dept = Department.objects.create(code="IT", name="Informatique")
        pos = Position.objects.create(code="DEV", title="Développeur", department=dept)

        emp = svc.create(first_name="Jean", last_name="Dupont", department_id=dept.id, position_id=pos.id)
        assert emp.status == "recruited"

        emp = svc.hire(emp.id)
        assert emp.status == "active"

        emp = svc.suspend(emp.id, reason="Suspension")
        assert emp.status == "suspended"

        emp = svc.terminate(emp.id, reason="Fin de contrat")
        assert emp.status == "terminated"

        assert EmployeeHistory.objects.filter(employee=emp).count() >= 3
        assert EmployeeAuditLog.objects.filter(employee=emp).count() >= 3
