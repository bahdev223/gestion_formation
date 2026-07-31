from typing import Optional

from django_rh.domain.entities.employee import EmployeeEntity
from django_rh.models import Employee


class EmployeeRepository:
    def get(self, *, organisation, employee_id: int) -> Optional[EmployeeEntity]:
        if organisation is None:
            raise ValueError("L'organisation est obligatoire.")
        try:
            emp = Employee.objects.get(
                id=employee_id,
                organisation=organisation,
            )
            return EmployeeEntity(
                id=emp.id, matricule=emp.matricule,
                first_name=emp.first_name, last_name=emp.last_name,
                sex=emp.sex, birth_date=emp.birth_date,
                phone=emp.phone, email=emp.email,
                status=emp.status,
                department_id=emp.department_id, position_id=emp.position_id,
                contract_type=emp.contract_type,
                hire_date=emp.hire_date, termination_date=emp.termination_date,
            )
        except Employee.DoesNotExist:
            return None
