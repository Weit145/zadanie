import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.storage.postgres.db_helper import db_helper
from app.transport.api.v1.schemas.category import (
    CreateCategory,
    OutCategory,
    UpdateCategory,
)
from app.usecase.service import service


router = APIRouter(tags=["Categories"])


@router.post(
    "/users/{user_id}/categories",
    status_code=status.HTTP_201_CREATED,
    response_model=OutCategory,
)
async def create_category(
    user_id: uuid.UUID,
    category: Annotated[CreateCategory, Body(title="The category data")],
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> OutCategory:
    return await service.create_category(user_id, category, session)


@router.get("/users/{user_id}/categories", response_model=list[OutCategory])
async def list_categories(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> list[OutCategory]:
    return await service.list_categories(user_id, session)


@router.get("/categories/{category_id}", response_model=OutCategory)
async def get_category(
    category_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> OutCategory:
    return await service.get_category(category_id, session)


@router.patch("/categories/{category_id}", response_model=OutCategory)
async def update_category(
    category_id: uuid.UUID,
    category: Annotated[UpdateCategory, Body(title="The category data")],
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> OutCategory:
    return await service.update_category(category_id, category, session)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> None:
    await service.delete_category(category_id, session)
