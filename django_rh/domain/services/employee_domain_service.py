from datetime import date
from django_rh.domain.entities.employee import EmployeeEntity
from django_rh.domain.value_objects.employee_status import EmployeeStatus
from django_rh.domain.validators.employee_validator import (
    validate_can_hire, validate_can_suspend, validate_can_terminate,
)


class EmployeeDomainService:
    def create_employee(self, first_name: str, last_name: str, sex: str = "M",
                        birth_date: date | None = None, phone: str = "", email: str = "",
                        department_id: int | None = None, position_id: int | None = None,
                        contract_type: str = "CDI") -> EmployeeEntity:
        return EmployeeEntity(
            first_name=first_name, last_name=last_name, sex=sex,
            birth_date=birth_date, phone=phone, email=email,
            department_id=department_id, position_id=position_id,
            contract_type=contract_type, status=EmployeeStatus.RECRUITED,
        )

    def hire(self, employee: EmployeeEntity) -> EmployeeEntity:
        validate_can_hire(employee.status, employee.id or 0)
        employee.status = EmployeeStatus.ACTIVE
        employee.hire_date = date.today()
        return employee

    def suspend(self, employee: EmployeeEntity) -> EmployeeEntity:
        validate_can_suspend(employee.status, employee.id or 0)
        employee.status = EmployeeStatus.SUSPENDED
        return employee

    def terminate(self, employee: EmployeeEntity) -> EmployeeEntity:
        validate_can_terminate(employee.status, employee.id or 0)
        employee.status = EmployeeStatus.TERMINATED
        employee.termination_date = date.today()
        return employee
