import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Category(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CreateCategory(Category):
    name: str = Field(..., min_length=1, max_length=80)
    color: str = Field("#4f46e5", pattern=r"^#[0-9a-fA-F]{6}$")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("category name must not be blank")
        return value


class UpdateCategory(Category):
    name: str | None = Field(None, min_length=1, max_length=80)
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("category name must not be blank")
        return value


class OutCategory(Category):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    color: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
