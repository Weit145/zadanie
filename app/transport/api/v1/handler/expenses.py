import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.storage.postgres.db_helper import db_helper
from app.transport.api.v1.schemas.expense import CreateExpense, Dashboard, OutExpense
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
) -> list[OutExpense]:
    return await service.list_month_expenses(user_id, year, month, session)


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
    return Response(
        content=build_dashboard_svg(analytics),
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
    svg = build_dashboard_svg(analytics)
    return HTMLResponse(content=build_dashboard_html(analytics, svg))
