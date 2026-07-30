from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class EmployeeEntity:
    id: Optional[int] = None
    matricule: str = ""
    first_name: str = ""
    last_name: str = ""
    sex: str = "M"
    birth_date: Optional[date] = None
    phone: str = ""
    email: str = ""
    status: str = "recruited"
    department_id: Optional[int] = None
    position_id: Optional[int] = None
    contract_type: str = "CDI"
    hire_date: Optional[date] = None
    termination_date: Optional[date] = None
    created_by_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
