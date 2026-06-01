import uuid
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.storage.models import (
    Category,
    Expense,
    MonthlyBudget,
    PaymentMethod,
    User,
)


class SQLAlchemyRepository:
    async def save(self, entity, session: AsyncSession):
        await session.flush()
        await session.refresh(entity)
        return entity

    async def create_user(self, user: User, session: AsyncSession) -> User:
        session.add(user)
        return await self.save(user, session)

    async def list_users(
        self,
        session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        stmt = select(User).order_by(desc(User.created_at)).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return list(result.scalars().all())

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

    async def delete_user(self, user: User, session: AsyncSession) -> None:
        await session.delete(user)

    async def create_expense(
        self,
        expense: Expense,
        session: AsyncSession,
    ) -> Expense:
        session.add(expense)
        return await self.save(expense, session)

    async def get_expense_by_id(
        self,
        expense_id: uuid.UUID,
        session: AsyncSession,
    ) -> Expense | None:
        return await session.get(Expense, expense_id)

    async def list_expenses(
        self,
        user_id: uuid.UUID,
        start_at: datetime | None,
        end_at: datetime | None,
        session: AsyncSession,
    ) -> list[Expense]:
        conditions = [Expense.user_id == user_id]
        if start_at is not None:
            conditions.append(Expense.spent_at >= start_at)
        if end_at is not None:
            conditions.append(Expense.spent_at < end_at)

        stmt = (
            select(Expense)
            .where(*conditions)
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

    async def create_category(
        self,
        category: Category,
        session: AsyncSession,
    ) -> Category:
        session.add(category)
        return await self.save(category, session)

    async def get_category_by_id(
        self,
        category_id: uuid.UUID,
        session: AsyncSession,
    ) -> Category | None:
        return await session.get(Category, category_id)

    async def get_category_by_name(
        self,
        user_id: uuid.UUID,
        name: str,
        session: AsyncSession,
    ) -> Category | None:
        stmt = select(Category).where(Category.user_id == user_id, Category.name == name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_categories(
        self,
        user_id: uuid.UUID,
        session: AsyncSession,
    ) -> list[Category]:
        stmt = select(Category).where(Category.user_id == user_id).order_by(Category.name)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def delete_category(
        self,
        category: Category,
        session: AsyncSession,
    ) -> None:
        await session.delete(category)

    async def create_payment_method(
        self,
        payment_method: PaymentMethod,
        session: AsyncSession,
    ) -> PaymentMethod:
        session.add(payment_method)
        return await self.save(payment_method, session)

    async def get_payment_method_by_id(
        self,
        payment_method_id: uuid.UUID,
        session: AsyncSession,
    ) -> PaymentMethod | None:
        return await session.get(PaymentMethod, payment_method_id)

    async def get_payment_method_by_name(
        self,
        user_id: uuid.UUID,
        name: str,
        session: AsyncSession,
    ) -> PaymentMethod | None:
        stmt = select(PaymentMethod).where(
            PaymentMethod.user_id == user_id,
            PaymentMethod.name == name,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_payment_methods(
        self,
        user_id: uuid.UUID,
        session: AsyncSession,
    ) -> list[PaymentMethod]:
        stmt = (
            select(PaymentMethod)
            .where(PaymentMethod.user_id == user_id)
            .order_by(PaymentMethod.name)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def delete_payment_method(
        self,
        payment_method: PaymentMethod,
        session: AsyncSession,
    ) -> None:
        await session.delete(payment_method)

    async def create_monthly_budget(
        self,
        budget: MonthlyBudget,
        session: AsyncSession,
    ) -> MonthlyBudget:
        session.add(budget)
        return await self.save(budget, session)

    async def get_monthly_budget_by_id(
        self,
        budget_id: uuid.UUID,
        session: AsyncSession,
    ) -> MonthlyBudget | None:
        return await session.get(MonthlyBudget, budget_id)

    async def get_monthly_budget(
        self,
        user_id: uuid.UUID,
        year: int,
        month: int,
        category_id: uuid.UUID | None,
        session: AsyncSession,
    ) -> MonthlyBudget | None:
        stmt = select(MonthlyBudget).where(
            MonthlyBudget.user_id == user_id,
            MonthlyBudget.year == year,
            MonthlyBudget.month == month,
        )
        if category_id is None:
            stmt = stmt.where(MonthlyBudget.category_id.is_(None))
        else:
            stmt = stmt.where(MonthlyBudget.category_id == category_id)

        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_monthly_budgets(
        self,
        user_id: uuid.UUID,
        session: AsyncSession,
        year: int | None = None,
        month: int | None = None,
        category_id: uuid.UUID | None = None,
    ) -> list[MonthlyBudget]:
        conditions = [MonthlyBudget.user_id == user_id]
        if year is not None:
            conditions.append(MonthlyBudget.year == year)
        if month is not None:
            conditions.append(MonthlyBudget.month == month)
        if category_id is not None:
            conditions.append(MonthlyBudget.category_id == category_id)

        stmt = (
            select(MonthlyBudget)
            .where(*conditions)
            .order_by(
                desc(MonthlyBudget.year),
                desc(MonthlyBudget.month),
                MonthlyBudget.category_id.is_not(None),
            )
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def delete_monthly_budget(
        self,
        budget: MonthlyBudget,
        session: AsyncSession,
    ) -> None:
        await session.delete(budget)


repository = SQLAlchemyRepository()
