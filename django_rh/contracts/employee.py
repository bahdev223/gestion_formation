from typing import Protocol, runtime_checkable


@runtime_checkable
class EmployeeContract(Protocol):
    def get_employee(self, employee_id: int) -> dict:
        ...

    def get_employee_name(self, employee_id: int) -> str:
        ...

    def is_employee_active(self, employee_id: int) -> bool:
        ...

    def get_department_employees(self, department_id: int) -> list[dict]:
        ...
