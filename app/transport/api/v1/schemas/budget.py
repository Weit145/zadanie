import datetime
import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MonthlyBudget(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CreateMonthlyBudget(MonthlyBudget):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    amount: Decimal = Field(..., gt=0)
    category_id: uuid.UUID | None = None


class UpdateMonthlyBudget(MonthlyBudget):
    year: int | None = Field(None, ge=2000, le=2100)
    month: int | None = Field(None, ge=1, le=12)
    amount: Decimal | None = Field(None, gt=0)
    category_id: uuid.UUID | None = None


class OutMonthlyBudget(MonthlyBudget):
    id: uuid.UUID
    user_id: uuid.UUID
    category_id: uuid.UUID | None
    year: int
    month: int
    amount: Decimal
    created_at: datetime.datetime
    updated_at: datetime.datetime


class CategoryBudgetStatus(BaseModel):
    category_id: uuid.UUID
    category: str
    budget: Decimal
    spent: Decimal
    remaining: Decimal
    percent_used: Decimal
    exceeded: bool


class BudgetStatus(BaseModel):
    year: int
    month: int
    budget: Decimal | None
    spent: Decimal
    remaining: Decimal | None
    percent_used: Decimal | None
    exceeded: bool
    category_budgets: list[CategoryBudgetStatus] = Field(default_factory=list)
