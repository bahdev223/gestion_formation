from typing import Protocol


class EmployeeEventContract(Protocol):
    def on_employee_created(self, employee_id: int, data: dict) -> None:
        ...

    def on_employee_hired(self, employee_id: int, data: dict) -> None:
        ...

    def on_employee_promoted(self, employee_id: int, data: dict) -> None:
        ...

    def on_employee_transferred(self, employee_id: int, data: dict) -> None:
        ...

    def on_employee_suspended(self, employee_id: int, data: dict) -> None:
        ...

    def on_employee_terminated(self, employee_id: int, data: dict) -> None:
        ...
