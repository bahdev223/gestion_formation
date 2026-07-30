import pytest
from django_rh.models import Employee


class TestEmployeeModel:
    def test_create_employee(self, db):
        emp = Employee.objects.create(matricule="EMP-000001", first_name="Jean", last_name="Dupont")
        assert emp.id is not None
        assert emp.status == Employee.Status.RECRUITED
