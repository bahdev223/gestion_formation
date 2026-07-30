from enum import Enum


class EmployeeStatus(str, Enum):
    RECRUITED = "recruited"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    ARCHIVED = "archived"

    @classmethod
    def can_hire(cls) -> list[str]:
        return [cls.RECRUITED.value]

    @classmethod
    def can_suspend(cls) -> list[str]:
        return [cls.ACTIVE.value]

    @classmethod
    def can_terminate(cls) -> list[str]:
        return [cls.ACTIVE.value, cls.SUSPENDED.value]
