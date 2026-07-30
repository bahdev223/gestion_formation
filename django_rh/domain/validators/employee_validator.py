from django_rh.domain.exceptions.rh_exceptions import (
    EmployeeAlreadyActiveError, EmployeeAlreadyTerminatedError,
    EmployeeCannotModifyError,
)
from django_rh.domain.value_objects.employee_status import EmployeeStatus


def validate_can_hire(status: str, employee_id: int):
    if status not in EmployeeStatus.can_hire():
        raise EmployeeAlreadyActiveError(employee_id)


def validate_can_suspend(status: str, employee_id: int):
    if status not in EmployeeStatus.can_suspend():
        raise EmployeeCannotModifyError(employee_id, status)


def validate_can_terminate(status: str, employee_id: int):
    if status not in EmployeeStatus.can_terminate():
        raise EmployeeAlreadyTerminatedError(employee_id)
