import pytest
from django_rh.services import EmployeeService
from django_rh.models import Employee


class TestEmployeeService:
    def test_create_employee(self, db):
        svc = EmployeeService()
        emp = svc.create(first_name="Jean", last_name="Dupont")
        assert emp.id is not None
        assert emp.status == "recruited"
        assert emp.matricule.startswith("EMP-")
        assert str(emp) == f"{emp.matricule} - Jean Dupont"

    def test_hire_employee(self, db):
        svc = EmployeeService()
        emp = svc.create(first_name="Jean", last_name="Dupont")
        emp = svc.hire(emp.id)
        assert emp.status == "active"
        assert emp.hire_date is not None

    def test_suspend_employee(self, db):
        svc = EmployeeService()
        emp = svc.create(first_name="Jean", last_name="Dupont")
        svc.hire(emp.id)
        emp = svc.suspend(emp.id, reason="Test")
        assert emp.status == "suspended"

    def test_terminate_employee(self, db):
        svc = EmployeeService()
        emp = svc.create(first_name="Jean", last_name="Dupont")
        svc.hire(emp.id)
        emp = svc.terminate(emp.id, reason="Démission")
        assert emp.status == "terminated"
        assert emp.termination_date is not None
