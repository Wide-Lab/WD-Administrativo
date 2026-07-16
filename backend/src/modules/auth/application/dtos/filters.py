from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UserFilters:
    q: str | None = None
    is_active: bool | None = True
