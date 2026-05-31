import datetime
import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


class Expense(BaseModel):
    pass


class CreateExpense(Expense):
    amount: Decimal = Field(..., gt=0, description="Expense amount")
    category: str = Field(..., min_length=1, max_length=80, description="Expense category")
    description: str | None = Field(None, max_length=255, description="Expense note")
    spent_at: datetime.datetime | None = Field(None, description="Expense date and time")


class OutExpense(Expense):
    id: uuid.UUID
    user_id: uuid.UUID
    amount: Decimal
    category: str
    description: str | None
    spent_at: datetime.datetime
    created_at: datetime.datetime


class CategorySummary(BaseModel):
    category: str
    total: Decimal
    percent: Decimal


class DailySummary(BaseModel):
    day: int
    total: Decimal


class Dashboard(BaseModel):
    year: int
    month: int
    total: Decimal
    count: int
    average_per_expense: Decimal
    average_per_day: Decimal
    categories: list[CategorySummary]
    daily: list[DailySummary]
