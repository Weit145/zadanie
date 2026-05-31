from dataclasses import dataclass

from app.domain.base import Entity


@dataclass(slots=True)
class User(Entity):
    name: str = ""
