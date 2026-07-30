from dataclasses import dataclass
from typing import Optional


@dataclass
class PositionEntity:
    id: Optional[int] = None
    code: str = ""
    title: str = ""
    description: str = ""
    department_id: Optional[int] = None
