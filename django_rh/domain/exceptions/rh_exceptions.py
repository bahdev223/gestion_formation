class RHError(Exception):
    pass


class EmployeeNotFoundError(RHError):
    def __init__(self, employee_id: int):
        self.employee_id = employee_id
        super().__init__(f"Employee #{employee_id} not found.")


class DepartmentNotFoundError(RHError):
    def __init__(self, department_id: int):
        self.department_id = department_id
        super().__init__(f"Department #{department_id} not found.")


class PositionNotFoundError(RHError):
    def __init__(self, position_id: int):
        self.position_id = position_id
        super().__init__(f"Position #{position_id} not found.")


class EmployeeAlreadyActiveError(RHError):
    def __init__(self, employee_id: int):
        self.employee_id = employee_id
        super().__init__(f"Employee #{employee_id} is already active.")


class EmployeeAlreadyTerminatedError(RHError):
    def __init__(self, employee_id: int):
        self.employee_id = employee_id
        super().__init__(f"Employee #{employee_id} is already terminated.")


class EmployeeCannotModifyError(RHError):
    def __init__(self, employee_id: int, status: str):
        self.employee_id = employee_id
        self.status = status
        super().__init__(f"Cannot modify employee #{employee_id} in status '{status}'.")
