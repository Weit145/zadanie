import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.storage.models import Expense, User
from app.repositories.storage.postgres.repositories import repository

from app.transport.api.v1.schemas.expense import (
    CreateExpense,
    Dashboard,
    OutExpense,
    CategorySummary,
    DailySummary,
)
from app.transport.api.v1.schemas.user import CreateUser, OutUser
from app.usecase.expense_analytics import (
    MonthlyAnalytics,
    build_month_period,
    build_monthly_analytics,
    normalize_category,
)


logger = logging.getLogger(__name__)


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _expense_to_schema(expense: Expense) -> OutExpense:
    return OutExpense(
        id=expense.id,
        user_id=expense.user_id,
        amount=expense.amount,
        category=expense.category,
        description=expense.description,
        spent_at=expense.spent_at,
        created_at=expense.created_at,
    )


def _analytics_to_schema(analytics: MonthlyAnalytics) -> Dashboard:
    return Dashboard(
        year=analytics.year,
        month=analytics.month,
        total=analytics.total,
        count=analytics.count,
        average_per_expense=analytics.average_per_expense,
        average_per_day=analytics.average_per_day,
        categories=[
            CategorySummary(
                category=item.category,
                total=item.total,
                percent=item.percent,
            )
            for item in analytics.categories
        ],
        daily=[
            DailySummary(day=item.day, total=item.total)
            for item in analytics.daily
        ],
    )


class Service:
    def __init__(self):
        self.repo = repository

    async def create_user(
        self,
        user: CreateUser,
        session: AsyncSession,
    ) -> OutUser:
        try:
            result = await self.repo.create_user(User(name=user.name), session)
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this name already exists",
            ) from exc

        await session.commit()
        return OutUser(
            id=result.id,
            name=result.name,
            created_at=result.created_at,
        )

    async def get_or_create_telegram_user(
        self,
        telegram_id: int,
        display_name: str | None,
        session: AsyncSession,
    ) -> User:
        user = await self.repo.get_user_by_telegram_id(telegram_id, session)
        if user is not None:
            return user

        clear_name = "_".join((display_name or "telegram").strip().split())
        clear_name = clear_name[:70] or "telegram"
        user_name = f"{clear_name}_{telegram_id}"

        try:
            result = await self.repo.create_user(
                User(name=user_name, telegram_id=telegram_id),
                session,
            )
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Telegram user already exists",
            ) from exc

        await session.commit()
        return result

    async def create_expense(
        self,
        user_id: uuid.UUID,
        expense: CreateExpense,
        session: AsyncSession,
    ) -> OutExpense:
        user = await self.repo.get_user_by_id(user_id, session)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        result = await self.repo.create_expense(
            Expense(
                user_id=user_id,
                amount=expense.amount,
                category=normalize_category(expense.category),
                description=expense.description,
                spent_at=_as_utc(expense.spent_at),
            ),
            session,
        )
        await session.commit()
        return _expense_to_schema(result)

    async def create_telegram_expense(
        self,
        telegram_id: int,
        display_name: str | None,
        expense: CreateExpense,
        session: AsyncSession,
    ) -> OutExpense:
        user = await self.get_or_create_telegram_user(
            telegram_id=telegram_id,
            display_name=display_name,
            session=session,
        )
        return await self.create_expense(user.id, expense, session)

    async def list_month_expenses(
        self,
        user_id: uuid.UUID,
        year: int | None,
        month: int | None,
        session: AsyncSession,
    ) -> list[OutExpense]:
        user = await self.repo.get_user_by_id(user_id, session)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        start_at, end_at = build_month_period(year=year, month=month)
        expenses = await self.repo.list_expenses(user_id, start_at, end_at, session)
        return [_expense_to_schema(expense) for expense in expenses]

    async def get_month_analytics(
        self,
        user_id: uuid.UUID,
        year: int | None,
        month: int | None,
        session: AsyncSession,
    ) -> MonthlyAnalytics:
        user = await self.repo.get_user_by_id(user_id, session)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        start_at, end_at = build_month_period(year=year, month=month)
        expenses = await self.repo.list_expenses(user_id, start_at, end_at, session)
        return build_monthly_analytics(expenses, start_at)

    async def get_month_dashboard(
        self,
        user_id: uuid.UUID,
        year: int | None,
        month: int | None,
        session: AsyncSession,
    ) -> Dashboard:
        analytics = await self.get_month_analytics(user_id, year, month, session)
        return _analytics_to_schema(analytics)

    async def get_telegram_month_analytics(
        self,
        telegram_id: int,
        display_name: str | None,
        year: int | None,
        month: int | None,
        session: AsyncSession,
    ) -> MonthlyAnalytics:
        user = await self.get_or_create_telegram_user(telegram_id, display_name, session)
        return await self.get_month_analytics(user.id, year, month, session)

    async def delete_last_telegram_expense(
        self,
        telegram_id: int,
        display_name: str | None,
        session: AsyncSession,
    ) -> OutExpense | None:
        user = await self.get_or_create_telegram_user(telegram_id, display_name, session)
        expense = await self.repo.get_last_expense(user.id, session)
        if expense is None:
            return None

        result = _expense_to_schema(expense)
        await self.repo.delete_expense(expense, session)
        await session.commit()
        return result

service = Service()
