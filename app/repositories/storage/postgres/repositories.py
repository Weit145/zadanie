import uuid
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.storage.models import Expense, User


class SQLAlchemyRepository:
    async def create_user(self, user: User, session: AsyncSession) -> User:
        session.add(user)
        await session.flush()
        await session.refresh(user)
        return user

    async def get_user_by_id(
        self,
        user_id: uuid.UUID,
        session: AsyncSession,
    ) -> User | None:
        return await session.get(User, user_id)

    async def get_user_by_telegram_id(
        self,
        telegram_id: int,
        session: AsyncSession,
    ) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_expense(
        self,
        expense: Expense,
        session: AsyncSession,
    ) -> Expense:
        session.add(expense)
        await session.flush()
        await session.refresh(expense)
        return expense

    async def list_expenses(
        self,
        user_id: uuid.UUID,
        start_at: datetime,
        end_at: datetime,
        session: AsyncSession,
    ) -> list[Expense]:
        stmt = (
            select(Expense)
            .where(
                Expense.user_id == user_id,
                Expense.spent_at >= start_at,
                Expense.spent_at < end_at,
            )
            .order_by(desc(Expense.spent_at))
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_last_expense(
        self,
        user_id: uuid.UUID,
        session: AsyncSession,
    ) -> Expense | None:
        stmt = (
            select(Expense)
            .where(Expense.user_id == user_id)
            .order_by(desc(Expense.spent_at), desc(Expense.created_at))
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_expense(
        self,
        expense: Expense,
        session: AsyncSession,
    ) -> None:
        await session.delete(expense)


repository = SQLAlchemyRepository()
