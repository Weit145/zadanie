import datetime
import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.base import Entity, utc_now


@dataclass(slots=True)
class Expense(Entity):
    user_id: uuid.UUID | None = None
    amount: Decimal = Decimal("0")
    category: str = ""
    description: str | None = None
    spent_at: datetime.datetime = field(default_factory=utc_now)
