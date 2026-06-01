import unittest
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.repositories.storage.models import Category, Expense, MonthlyBudget, User
from app.transport.api.v1.schemas.budget import CreateMonthlyBudget
from app.transport.api.v1.schemas.expense import CreateExpense
from app.usecase.service import Service


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeRepository:
    def __init__(self) -> None:
        self.users: dict[uuid.UUID, User] = {}
        self.categories: dict[uuid.UUID, Category] = {}
        self.expenses: dict[uuid.UUID, Expense] = {}
        self.budgets: dict[uuid.UUID, MonthlyBudget] = {}

    async def save(self, entity, session):
        self._ensure_identity(entity)
        return entity

    async def create_user(self, user: User, session) -> User:
        self._ensure_identity(user)
        self.users[user.id] = user
        return user

    async def get_user_by_id(self, user_id: uuid.UUID, session) -> User | None:
        return self.users.get(user_id)

    async def get_user_by_telegram_id(self, telegram_id: int, session) -> User | None:
        return next(
            (user for user in self.users.values() if user.telegram_id == telegram_id),
            None,
        )

    async def create_category(self, category: Category, session) -> Category:
        self._ensure_identity(category)
        self.categories[category.id] = category
        return category

    async def get_category_by_id(self, category_id: uuid.UUID, session) -> Category | None:
        return self.categories.get(category_id)

    async def get_category_by_name(
        self,
        user_id: uuid.UUID,
        name: str,
        session,
    ) -> Category | None:
        return next(
            (
                category
                for category in self.categories.values()
                if category.user_id == user_id and category.name == name
            ),
            None,
        )

    async def list_categories(self, user_id: uuid.UUID, session) -> list[Category]:
        return [category for category in self.categories.values() if category.user_id == user_id]

    async def create_expense(self, expense: Expense, session) -> Expense:
        self._ensure_identity(expense)
        self.expenses[expense.id] = expense
        return expense

    async def list_expenses(
        self,
        user_id: uuid.UUID,
        start_at: datetime | None,
        end_at: datetime | None,
        session,
    ) -> list[Expense]:
        expenses = [expense for expense in self.expenses.values() if expense.user_id == user_id]
        if start_at is not None:
            expenses = [expense for expense in expenses if expense.spent_at >= start_at]
        if end_at is not None:
            expenses = [expense for expense in expenses if expense.spent_at < end_at]
        return expenses

    async def get_last_expense(self, user_id: uuid.UUID, session) -> Expense | None:
        expenses = [expense for expense in self.expenses.values() if expense.user_id == user_id]
        return max(expenses, key=lambda item: (item.spent_at, item.created_at), default=None)

    async def delete_expense(self, expense: Expense, session) -> None:
        self.expenses.pop(expense.id, None)

    async def create_monthly_budget(self, budget: MonthlyBudget, session) -> MonthlyBudget:
        self._ensure_identity(budget)
        self.budgets[budget.id] = budget
        return budget

    async def get_monthly_budget(
        self,
        user_id: uuid.UUID,
        year: int,
        month: int,
        category_id: uuid.UUID | None,
        session,
    ) -> MonthlyBudget | None:
        return next(
            (
                budget
                for budget in self.budgets.values()
                if budget.user_id == user_id
                and budget.year == year
                and budget.month == month
                and budget.category_id == category_id
            ),
            None,
        )

    async def list_monthly_budgets(
        self,
        user_id: uuid.UUID,
        session,
        year: int | None = None,
        month: int | None = None,
        category_id: uuid.UUID | None = None,
    ) -> list[MonthlyBudget]:
        return [
            budget
            for budget in self.budgets.values()
            if budget.user_id == user_id
            and (year is None or budget.year == year)
            and (month is None or budget.month == month)
            and (category_id is None or budget.category_id == category_id)
        ]

    def _ensure_identity(self, entity) -> None:
        now = datetime.now(timezone.utc)
        if getattr(entity, "id", None) is None:
            entity.id = uuid.uuid4()
        if hasattr(entity, "created_at") and getattr(entity, "created_at", None) is None:
            entity.created_at = now
        if hasattr(entity, "updated_at") and getattr(entity, "updated_at", None) is None:
            entity.updated_at = now
        if isinstance(entity, Expense) and getattr(entity, "spent_at", None) is None:
            entity.spent_at = now


class ServiceCrudTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.service = Service()
        self.service.repo = FakeRepository()
        self.session = FakeSession()

    async def test_get_or_create_telegram_user(self) -> None:
        first = await self.service.get_or_create_telegram_user(10, "Alice", self.session)
        second = await self.service.get_or_create_telegram_user(10, "Alice", self.session)

        self.assertEqual(first.id, second.id)
        self.assertEqual(first.telegram_id, 10)

    async def test_create_expense_with_automatic_category_and_delete_last(self) -> None:
        user = await self.service.get_or_create_telegram_user(11, "Bob", self.session)
        expense = await self.service.create_expense(
            user.id,
            CreateExpense(amount=Decimal("125.00"), category="Cafe"),
            self.session,
        )
        categories = await self.service.list_categories(user.id, self.session)
        deleted = await self.service.delete_last_telegram_expense(11, "Bob", self.session)

        self.assertEqual(expense.category, "cafe")
        self.assertEqual(len(categories), 1)
        self.assertEqual(categories[0].name, "cafe")
        self.assertIsNotNone(deleted)
        self.assertEqual(deleted.id, expense.id)

    async def test_create_budget_and_budget_status(self) -> None:
        user = await self.service.get_or_create_telegram_user(12, "Cara", self.session)
        budget = await self.service.create_monthly_budget(
            user.id,
            CreateMonthlyBudget(year=2026, month=5, amount=Decimal("500.00")),
            self.session,
        )
        await self.service.create_expense(
            user.id,
            CreateExpense(
                amount=Decimal("125.00"),
                category="products",
                spent_at=datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc),
            ),
            self.session,
        )
        status = await self.service.get_budget_status(user.id, 2026, 5, self.session)

        self.assertEqual(budget.amount, Decimal("500.00"))
        self.assertEqual(status.spent, Decimal("125.00"))
        self.assertEqual(status.remaining, Decimal("375.00"))
        self.assertFalse(status.exceeded)

    async def test_expenses_do_not_mix_between_months_and_users(self) -> None:
        first_user = await self.service.get_or_create_telegram_user(13, "Dina", self.session)
        second_user = await self.service.get_or_create_telegram_user(14, "Egor", self.session)
        await self.service.create_expense(
            first_user.id,
            CreateExpense(
                amount=Decimal("100.00"),
                category="food",
                spent_at=datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc),
            ),
            self.session,
        )
        await self.service.create_expense(
            first_user.id,
            CreateExpense(
                amount=Decimal("300.00"),
                category="food",
                spent_at=datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc),
            ),
            self.session,
        )
        await self.service.create_expense(
            second_user.id,
            CreateExpense(
                amount=Decimal("900.00"),
                category="food",
                spent_at=datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc),
            ),
            self.session,
        )

        first_may = await self.service.get_month_analytics(first_user.id, 2026, 5, self.session)
        first_june = await self.service.get_month_analytics(first_user.id, 2026, 6, self.session)
        second_may = await self.service.get_month_analytics(second_user.id, 2026, 5, self.session)

        self.assertEqual(first_may.total, Decimal("100.00"))
        self.assertEqual(first_june.total, Decimal("300.00"))
        self.assertEqual(second_may.total, Decimal("900.00"))
