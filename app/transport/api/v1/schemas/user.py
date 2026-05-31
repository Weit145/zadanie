import datetime
import uuid
from pydantic import BaseModel, Field


class User(BaseModel):
    pass


class CreateUser(User):
    name: str = Field(..., description="Name of the user")

class OutUser(User):
    id: uuid.UUID
    name: str = Field(..., description="Name of the user")
    created_at: datetime.datetime
