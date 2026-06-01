import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PaymentMethod(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CreatePaymentMethod(PaymentMethod):
    name: str = Field(..., min_length=1, max_length=80)
    method_type: str = Field("other", min_length=1, max_length=40)

    @field_validator("name", "method_type")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value


class UpdatePaymentMethod(PaymentMethod):
    name: str | None = Field(None, min_length=1, max_length=80)
    method_type: str | None = Field(None, min_length=1, max_length=40)

    @field_validator("name", "method_type")
    @classmethod
    def validate_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("value must not be blank")
        return value


class OutPaymentMethod(PaymentMethod):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    method_type: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
