from typing import Optional, Protocol

from django_rh.domain.entities.employee import EmployeeEntity


class EmployeeRepositoryInterface(Protocol):
    def get(
        self,
        *,
        organisation,
        employee_id: int,
    ) -> Optional[EmployeeEntity]:
        ...

    def save(self, entity: EmployeeEntity) -> EmployeeEntity:
        ...

    def delete(self, employee_id: int) -> None:
        ...
