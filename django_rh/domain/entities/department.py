from dataclasses import dataclass
from typing import Optional


@dataclass
class DepartmentEntity:
    id: Optional[int] = None
    code: str = ""
    name: str = ""
    description: str = ""
    manager_id: Optional[int] = None
