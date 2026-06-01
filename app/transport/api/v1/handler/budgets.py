import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.storage.postgres.db_helper import db_helper
from app.transport.api.v1.schemas.budget import (
    CreateMonthlyBudget,
    OutMonthlyBudget,
    UpdateMonthlyBudget,
)
from app.usecase.service import service


router = APIRouter(tags=["Budgets"])


@router.post(
    "/users/{user_id}/budgets",
    status_code=status.HTTP_201_CREATED,
    response_model=OutMonthlyBudget,
)
async def create_budget(
    user_id: uuid.UUID,
    budget: Annotated[CreateMonthlyBudget, Body(title="The monthly budget data")],
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> OutMonthlyBudget:
    return await service.create_monthly_budget(user_id, budget, session)


@router.get("/users/{user_id}/budgets", response_model=list[OutMonthlyBudget])
async def list_budgets(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
    category_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[OutMonthlyBudget]:
    return await service.list_monthly_budgets(
        user_id=user_id,
        session=session,
        year=year,
        month=month,
        category_id=category_id,
    )


@router.get("/budgets/{budget_id}", response_model=OutMonthlyBudget)
async def get_budget(
    budget_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> OutMonthlyBudget:
    return await service.get_monthly_budget(budget_id, session)


@router.patch("/budgets/{budget_id}", response_model=OutMonthlyBudget)
async def update_budget(
    budget_id: uuid.UUID,
    budget: Annotated[UpdateMonthlyBudget, Body(title="The monthly budget data")],
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> OutMonthlyBudget:
    return await service.update_monthly_budget(budget_id, budget, session)


@router.delete("/budgets/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> None:
    await service.delete_monthly_budget(budget_id, session)
