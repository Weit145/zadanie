import datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CreateUser(User):
    name: str = Field(..., min_length=1, max_length=100, description="Name of the user")
    telegram_id: int | None = Field(None, description="Telegram account id")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("user name must not be blank")
        return value


class UpdateUser(User):
    name: str | None = Field(None, min_length=1, max_length=100, description="Name of the user")
    telegram_id: int | None = Field(None, description="Telegram account id")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("user name must not be blank")
        return value


class OutUser(User):
    id: uuid.UUID
    name: str = Field(..., description="Name of the user")
    telegram_id: int | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
