import datetime
import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.transport.api.v1.schemas.budget import BudgetStatus


class Expense(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CreateExpense(Expense):
    amount: Decimal = Field(..., gt=0, description="Expense amount")
    category: str | None = Field(None, min_length=1, max_length=80, description="Expense category")
    category_id: uuid.UUID | None = Field(None, description="Expense category id")
    payment_method_id: uuid.UUID | None = Field(None, description="Payment method id")
    description: str | None = Field(None, max_length=255, description="Expense note")
    spent_at: datetime.datetime | None = Field(None, description="Expense date and time")

    @model_validator(mode="after")
    def require_category(self) -> "CreateExpense":
        if self.category is None and self.category_id is None:
            raise ValueError("category or category_id is required")
        return self

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("category must not be blank")
        return value


class UpdateExpense(Expense):
    amount: Decimal | None = Field(None, gt=0, description="Expense amount")
    category: str | None = Field(None, min_length=1, max_length=80, description="Expense category")
    category_id: uuid.UUID | None = Field(None, description="Expense category id")
    payment_method_id: uuid.UUID | None = Field(None, description="Payment method id")
    description: str | None = Field(None, max_length=255, description="Expense note")
    spent_at: datetime.datetime | None = Field(None, description="Expense date and time")

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("category must not be blank")
        return value


class OutExpense(Expense):
    id: uuid.UUID
    user_id: uuid.UUID
    category_id: uuid.UUID | None = None
    payment_method_id: uuid.UUID | None = None
    amount: Decimal
    category: str
    description: str | None
    spent_at: datetime.datetime
    created_at: datetime.datetime
    updated_at: datetime.datetime


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
    budget: BudgetStatus | None = None
