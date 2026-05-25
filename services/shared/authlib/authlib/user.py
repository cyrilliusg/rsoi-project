"""
Lightweight user dataclass passed to views as request.user after JWT auth.
Intentionally minimal — backend services do not have a local user DB.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class LightUser:
    sub: str
    username: str
    role: str
    email: Optional[str] = None
    name: Optional[str] = None
    scope: List[str] = field(default_factory=list)
    is_authenticated: bool = True

    @property
    def is_admin(self) -> bool:
        return self.role == "ADMIN"
