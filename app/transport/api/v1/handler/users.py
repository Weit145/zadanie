from fastapi import APIRouter, status, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from app.repositories.storage.postgres.db_helper import db_helper
from app.transport.api.v1.schemas.user import CreateUser, OutUser
from app.usecase.service import service

router = APIRouter(tags=["Users"])


@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=OutUser)
async def create_user(
    user: Annotated[CreateUser, Body(title="The user data")],
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> OutUser:
    return await service.create_user(user, session)

