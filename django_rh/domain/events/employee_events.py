from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class EmployeeEvent:
    name: str
    employee_id: int
    data: dict
    performed_by_id: Optional[int] = None
    performed_at: datetime = field(default_factory=datetime.now)


class EmployeeEvents:
    CREATED = "employee.created"
    HIRED = "employee.hired"
    PROMOTED = "employee.promoted"
    TRANSFERRED = "employee.transferred"
    SUSPENDED = "employee.suspended"
    TERMINATED = "employee.terminated"
