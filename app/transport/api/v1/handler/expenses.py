import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.storage.postgres.db_helper import db_helper
from app.transport.api.v1.schemas.budget import BudgetStatus
from app.transport.api.v1.schemas.expense import (
    CreateExpense,
    Dashboard,
    OutExpense,
    UpdateExpense,
)
from app.usecase.expense_analytics import build_dashboard_html, build_dashboard_svg
from app.usecase.service import service


router = APIRouter(tags=["Expenses"])


@router.post(
    "/users/{user_id}/expenses",
    status_code=status.HTTP_201_CREATED,
    response_model=OutExpense,
)
async def create_expense(
    user_id: uuid.UUID,
    expense: Annotated[CreateExpense, Body(title="The expense data")],
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> OutExpense:
    return await service.create_expense(user_id, expense, session)


@router.get("/users/{user_id}/expenses", response_model=list[OutExpense])
async def list_expenses(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
    start_at: Annotated[datetime | None, Query()] = None,
    end_at: Annotated[datetime | None, Query()] = None,
) -> list[OutExpense]:
    return await service.list_month_expenses(
        user_id=user_id,
        year=year,
        month=month,
        session=session,
        start_at=start_at,
        end_at=end_at,
    )


@router.get("/expenses/{expense_id}", response_model=OutExpense)
async def get_expense(
    expense_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> OutExpense:
    return await service.get_expense(expense_id, session)


@router.patch("/expenses/{expense_id}", response_model=OutExpense)
async def update_expense(
    expense_id: uuid.UUID,
    expense: Annotated[UpdateExpense, Body(title="The expense data")],
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> OutExpense:
    return await service.update_expense(expense_id, expense, session)


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> None:
    await service.delete_expense(expense_id, session)


@router.get("/users/{user_id}/dashboard", response_model=Dashboard)
async def get_dashboard(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
) -> Dashboard:
    return await service.get_month_dashboard(user_id, year, month, session)


@router.get("/users/{user_id}/dashboard.svg")
async def get_dashboard_svg(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
) -> Response:
    analytics = await service.get_month_analytics(user_id, year, month, session)
    budget = await service.get_budget_status(user_id, analytics.year, analytics.month, session)
    return Response(
        content=build_dashboard_svg(analytics, budget),
        media_type="image/svg+xml",
    )


@router.get("/users/{user_id}/dashboard.html", response_class=HTMLResponse)
async def get_dashboard_html(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
) -> HTMLResponse:
    analytics = await service.get_month_analytics(user_id, year, month, session)
    budget = await service.get_budget_status(user_id, analytics.year, analytics.month, session)
    svg = build_dashboard_svg(analytics, budget)
    return HTMLResponse(content=build_dashboard_html(analytics, svg, budget))


@router.get("/users/{user_id}/budget-status", response_model=BudgetStatus)
async def get_budget_status(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
) -> BudgetStatus:
    return await service.get_budget_status(user_id, year, month, session)
