import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.storage.postgres.db_helper import db_helper
from app.transport.api.v1.schemas.user import CreateUser, OutUser, UpdateUser
from app.usecase.service import service

router = APIRouter(tags=["Users"])


@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=OutUser)
async def create_user(
    user: Annotated[CreateUser, Body(title="The user data")],
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> OutUser:
    return await service.create_user(user, session)


@router.get("/users", response_model=list[OutUser])
async def list_users(
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[OutUser]:
    return await service.list_users(session=session, limit=limit, offset=offset)


@router.get("/users/{user_id}", response_model=OutUser)
async def get_user(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> OutUser:
    return await service.get_user(user_id, session)


@router.patch("/users/{user_id}", response_model=OutUser)
async def update_user(
    user_id: uuid.UUID,
    user: Annotated[UpdateUser, Body(title="The user data")],
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> OutUser:
    return await service.update_user(user_id, user, session)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> None:
    await service.delete_user(user_id, session)
