import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.storage.models import (
    Category,
    Expense,
    MonthlyBudget,
    PaymentMethod,
    User,
)
from app.repositories.storage.postgres.repositories import repository
from app.transport.api.v1.schemas.budget import (
    BudgetStatus,
    CategoryBudgetStatus,
    CreateMonthlyBudget,
    OutMonthlyBudget,
    UpdateMonthlyBudget,
)
from app.transport.api.v1.schemas.category import (
    CreateCategory,
    OutCategory,
    UpdateCategory,
)
from app.transport.api.v1.schemas.expense import (
    CategorySummary,
    CreateExpense,
    DailySummary,
    Dashboard,
    OutExpense,
    UpdateExpense,
)
from app.transport.api.v1.schemas.payment_method import (
    CreatePaymentMethod,
    OutPaymentMethod,
    UpdatePaymentMethod,
)
from app.transport.api.v1.schemas.user import CreateUser, OutUser, UpdateUser
from app.usecase.expense_analytics import (
    MonthlyAnalytics,
    build_month_period,
    build_monthly_analytics,
    normalize_category,
    to_money,
)


logger = logging.getLogger(__name__)


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_name(value: str) -> str:
    return normalize_category(value)


def _normalize_payment_type(value: str | None) -> str:
    normalized = " ".join((value or "other").strip().lower().split())
    return normalized or "other"


def _user_to_schema(user: User) -> OutUser:
    return OutUser(
        id=user.id,
        name=user.name,
        telegram_id=user.telegram_id,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _expense_to_schema(expense: Expense) -> OutExpense:
    return OutExpense(
        id=expense.id,
        user_id=expense.user_id,
        category_id=expense.category_id,
        payment_method_id=expense.payment_method_id,
        amount=expense.amount,
        category=expense.category,
        description=expense.description,
        spent_at=expense.spent_at,
        created_at=expense.created_at,
        updated_at=expense.updated_at,
    )


def _category_to_schema(category: Category) -> OutCategory:
    return OutCategory(
        id=category.id,
        user_id=category.user_id,
        name=category.name,
        color=category.color,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


def _payment_method_to_schema(payment_method: PaymentMethod) -> OutPaymentMethod:
    return OutPaymentMethod(
        id=payment_method.id,
        user_id=payment_method.user_id,
        name=payment_method.name,
        method_type=payment_method.method_type,
        created_at=payment_method.created_at,
        updated_at=payment_method.updated_at,
    )


def _budget_to_schema(budget: MonthlyBudget) -> OutMonthlyBudget:
    return OutMonthlyBudget(
        id=budget.id,
        user_id=budget.user_id,
        category_id=budget.category_id,
        year=budget.year,
        month=budget.month,
        amount=budget.amount,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


def _analytics_to_schema(
    analytics: MonthlyAnalytics,
    budget: BudgetStatus | None = None,
) -> Dashboard:
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
        budget=budget,
    )


def _raise_not_found(detail: str) -> None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


async def _raise_conflict(
    session: AsyncSession,
    detail: str,
    exc: IntegrityError,
) -> None:
    await session.rollback()
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc


class Service:
    def __init__(self):
        self.repo = repository

    async def _get_user_or_404(
        self,
        user_id: uuid.UUID,
        session: AsyncSession,
    ) -> User:
        user = await self.repo.get_user_by_id(user_id, session)
        if user is None:
            _raise_not_found("User not found")
        return user

    async def _get_category_or_404(
        self,
        category_id: uuid.UUID,
        session: AsyncSession,
    ) -> Category:
        category = await self.repo.get_category_by_id(category_id, session)
        if category is None:
            _raise_not_found("Category not found")
        return category

    async def _get_payment_method_or_404(
        self,
        payment_method_id: uuid.UUID,
        session: AsyncSession,
    ) -> PaymentMethod:
        payment_method = await self.repo.get_payment_method_by_id(payment_method_id, session)
        if payment_method is None:
            _raise_not_found("Payment method not found")
        return payment_method

    async def _get_budget_or_404(
        self,
        budget_id: uuid.UUID,
        session: AsyncSession,
    ) -> MonthlyBudget:
        budget = await self.repo.get_monthly_budget_by_id(budget_id, session)
        if budget is None:
            _raise_not_found("Budget not found")
        return budget

    async def _ensure_category_for_user(
        self,
        user_id: uuid.UUID,
        session: AsyncSession,
        category_id: uuid.UUID | None = None,
        category_name: str | None = None,
        color: str = "#4f46e5",
    ) -> Category:
        if category_id is not None:
            category = await self._get_category_or_404(category_id, session)
            if category.user_id != user_id:
                _raise_not_found("Category not found")
            return category

        name = _normalize_name(category_name or "")
        category = await self.repo.get_category_by_name(user_id, name, session)
        if category is not None:
            return category

        return await self.repo.create_category(
            Category(user_id=user_id, name=name, color=color),
            session,
        )

    async def _ensure_payment_method_for_user(
        self,
        user_id: uuid.UUID,
        payment_method_id: uuid.UUID | None,
        session: AsyncSession,
    ) -> PaymentMethod | None:
        if payment_method_id is None:
            return None
        payment_method = await self._get_payment_method_or_404(payment_method_id, session)
        if payment_method.user_id != user_id:
            _raise_not_found("Payment method not found")
        return payment_method

    async def create_user(
        self,
        user: CreateUser,
        session: AsyncSession,
    ) -> OutUser:
        try:
            result = await self.repo.create_user(
                User(name=user.name.strip(), telegram_id=user.telegram_id),
                session,
            )
            await session.commit()
        except IntegrityError as exc:
            await _raise_conflict(session, "User with this name or telegram_id already exists", exc)
        return _user_to_schema(result)

    async def list_users(
        self,
        session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
    ) -> list[OutUser]:
        users = await self.repo.list_users(session=session, limit=limit, offset=offset)
        return [_user_to_schema(user) for user in users]

    async def get_user(
        self,
        user_id: uuid.UUID,
        session: AsyncSession,
    ) -> OutUser:
        return _user_to_schema(await self._get_user_or_404(user_id, session))

    async def update_user(
        self,
        user_id: uuid.UUID,
        payload: UpdateUser,
        session: AsyncSession,
    ) -> OutUser:
        user = await self._get_user_or_404(user_id, session)
        data = payload.model_dump(exclude_unset=True)
        if "name" in data and data["name"] is not None:
            user.name = data["name"].strip()
        if "telegram_id" in data:
            user.telegram_id = data["telegram_id"]
        user.updated_at = datetime.now(timezone.utc)

        try:
            result = await self.repo.save(user, session)
            await session.commit()
        except IntegrityError as exc:
            await _raise_conflict(session, "User with this name or telegram_id already exists", exc)
        return _user_to_schema(result)

    async def delete_user(
        self,
        user_id: uuid.UUID,
        session: AsyncSession,
    ) -> None:
        user = await self._get_user_or_404(user_id, session)
        await self.repo.delete_user(user, session)
        await session.commit()

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
            await session.commit()
        except IntegrityError as exc:
            await _raise_conflict(session, "Telegram user already exists", exc)
        return result

    async def create_expense(
        self,
        user_id: uuid.UUID,
        expense: CreateExpense,
        session: AsyncSession,
    ) -> OutExpense:
        await self._get_user_or_404(user_id, session)

        try:
            category = await self._ensure_category_for_user(
                user_id=user_id,
                category_id=expense.category_id,
                category_name=expense.category,
                session=session,
            )
            payment_method = await self._ensure_payment_method_for_user(
                user_id,
                expense.payment_method_id,
                session,
            )
            result = await self.repo.create_expense(
                Expense(
                    user_id=user_id,
                    category_id=category.id,
                    payment_method_id=payment_method.id if payment_method else None,
                    amount=expense.amount,
                    category=category.name,
                    description=expense.description,
                    spent_at=_as_utc(expense.spent_at),
                ),
                session,
            )
            await session.commit()
        except IntegrityError as exc:
            await _raise_conflict(session, "Expense could not be created because of conflicting data", exc)
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
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[OutExpense]:
        await self._get_user_or_404(user_id, session)

        if start_at is None and end_at is None:
            start_at, end_at = build_month_period(year=year, month=month)
        else:
            start_at = _as_utc(start_at) if start_at else None
            end_at = _as_utc(end_at) if end_at else None

        expenses = await self.repo.list_expenses(user_id, start_at, end_at, session)
        return [_expense_to_schema(expense) for expense in expenses]

    async def get_expense(
        self,
        expense_id: uuid.UUID,
        session: AsyncSession,
    ) -> OutExpense:
        expense = await self.repo.get_expense_by_id(expense_id, session)
        if expense is None:
            _raise_not_found("Expense not found")
        return _expense_to_schema(expense)

    async def update_expense(
        self,
        expense_id: uuid.UUID,
        payload: UpdateExpense,
        session: AsyncSession,
    ) -> OutExpense:
        expense = await self.repo.get_expense_by_id(expense_id, session)
        if expense is None:
            _raise_not_found("Expense not found")

        data = payload.model_dump(exclude_unset=True)
        try:
            if "amount" in data and data["amount"] is not None:
                expense.amount = data["amount"]
            if "description" in data:
                expense.description = data["description"]
            if "spent_at" in data and data["spent_at"] is not None:
                expense.spent_at = _as_utc(data["spent_at"])
            if "payment_method_id" in data:
                payment_method = await self._ensure_payment_method_for_user(
                    expense.user_id,
                    data["payment_method_id"],
                    session,
                )
                expense.payment_method_id = payment_method.id if payment_method else None
            if "category_id" in data and data["category_id"] is not None:
                category = await self._ensure_category_for_user(
                    user_id=expense.user_id,
                    category_id=data["category_id"],
                    session=session,
                )
                expense.category_id = category.id
                expense.category = category.name
            elif "category" in data and data["category"] is not None:
                category = await self._ensure_category_for_user(
                    user_id=expense.user_id,
                    category_name=data["category"],
                    session=session,
                )
                expense.category_id = category.id
                expense.category = category.name
            elif data.get("category_id") is None and "category_id" in data:
                expense.category_id = None
            expense.updated_at = datetime.now(timezone.utc)

            result = await self.repo.save(expense, session)
            await session.commit()
        except IntegrityError as exc:
            await _raise_conflict(session, "Expense could not be updated because of conflicting data", exc)
        return _expense_to_schema(result)

    async def delete_expense(
        self,
        expense_id: uuid.UUID,
        session: AsyncSession,
    ) -> None:
        expense = await self.repo.get_expense_by_id(expense_id, session)
        if expense is None:
            _raise_not_found("Expense not found")
        await self.repo.delete_expense(expense, session)
        await session.commit()

    async def create_category(
        self,
        user_id: uuid.UUID,
        payload: CreateCategory,
        session: AsyncSession,
    ) -> OutCategory:
        await self._get_user_or_404(user_id, session)
        try:
            category = await self.repo.create_category(
                Category(
                    user_id=user_id,
                    name=_normalize_name(payload.name),
                    color=payload.color.lower(),
                ),
                session,
            )
            await session.commit()
        except IntegrityError as exc:
            await _raise_conflict(session, "Category with this name already exists", exc)
        return _category_to_schema(category)

    async def list_categories(
        self,
        user_id: uuid.UUID,
        session: AsyncSession,
    ) -> list[OutCategory]:
        await self._get_user_or_404(user_id, session)
        categories = await self.repo.list_categories(user_id, session)
        return [_category_to_schema(category) for category in categories]

    async def get_category(
        self,
        category_id: uuid.UUID,
        session: AsyncSession,
    ) -> OutCategory:
        return _category_to_schema(await self._get_category_or_404(category_id, session))

    async def update_category(
        self,
        category_id: uuid.UUID,
        payload: UpdateCategory,
        session: AsyncSession,
    ) -> OutCategory:
        category = await self._get_category_or_404(category_id, session)
        data = payload.model_dump(exclude_unset=True)
        if "name" in data and data["name"] is not None:
            category.name = _normalize_name(data["name"])
        if "color" in data and data["color"] is not None:
            category.color = data["color"].lower()
        category.updated_at = datetime.now(timezone.utc)

        try:
            result = await self.repo.save(category, session)
            await session.commit()
        except IntegrityError as exc:
            await _raise_conflict(session, "Category with this name already exists", exc)
        return _category_to_schema(result)

    async def delete_category(
        self,
        category_id: uuid.UUID,
        session: AsyncSession,
    ) -> None:
        category = await self._get_category_or_404(category_id, session)
        await self.repo.delete_category(category, session)
        await session.commit()

    async def create_payment_method(
        self,
        user_id: uuid.UUID,
        payload: CreatePaymentMethod,
        session: AsyncSession,
    ) -> OutPaymentMethod:
        await self._get_user_or_404(user_id, session)
        try:
            payment_method = await self.repo.create_payment_method(
                PaymentMethod(
                    user_id=user_id,
                    name=_normalize_name(payload.name),
                    method_type=_normalize_payment_type(payload.method_type),
                ),
                session,
            )
            await session.commit()
        except IntegrityError as exc:
            await _raise_conflict(session, "Payment method with this name already exists", exc)
        return _payment_method_to_schema(payment_method)

    async def list_payment_methods(
        self,
        user_id: uuid.UUID,
        session: AsyncSession,
    ) -> list[OutPaymentMethod]:
        await self._get_user_or_404(user_id, session)
        methods = await self.repo.list_payment_methods(user_id, session)
        return [_payment_method_to_schema(method) for method in methods]

    async def get_payment_method(
        self,
        payment_method_id: uuid.UUID,
        session: AsyncSession,
    ) -> OutPaymentMethod:
        method = await self._get_payment_method_or_404(payment_method_id, session)
        return _payment_method_to_schema(method)

    async def update_payment_method(
        self,
        payment_method_id: uuid.UUID,
        payload: UpdatePaymentMethod,
        session: AsyncSession,
    ) -> OutPaymentMethod:
        method = await self._get_payment_method_or_404(payment_method_id, session)
        data = payload.model_dump(exclude_unset=True)
        if "name" in data and data["name"] is not None:
            method.name = _normalize_name(data["name"])
        if "method_type" in data and data["method_type"] is not None:
            method.method_type = _normalize_payment_type(data["method_type"])
        method.updated_at = datetime.now(timezone.utc)

        try:
            result = await self.repo.save(method, session)
            await session.commit()
        except IntegrityError as exc:
            await _raise_conflict(session, "Payment method with this name already exists", exc)
        return _payment_method_to_schema(result)

    async def delete_payment_method(
        self,
        payment_method_id: uuid.UUID,
        session: AsyncSession,
    ) -> None:
        method = await self._get_payment_method_or_404(payment_method_id, session)
        await self.repo.delete_payment_method(method, session)
        await session.commit()

    async def create_monthly_budget(
        self,
        user_id: uuid.UUID,
        payload: CreateMonthlyBudget,
        session: AsyncSession,
    ) -> OutMonthlyBudget:
        await self._get_user_or_404(user_id, session)
        category_id = await self._validate_budget_category(user_id, payload.category_id, session)
        existing = await self.repo.get_monthly_budget(
            user_id=user_id,
            year=payload.year,
            month=payload.month,
            category_id=category_id,
            session=session,
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Budget for this month and category already exists",
            )

        try:
            budget = await self.repo.create_monthly_budget(
                MonthlyBudget(
                    user_id=user_id,
                    category_id=category_id,
                    year=payload.year,
                    month=payload.month,
                    amount=payload.amount,
                ),
                session,
            )
            await session.commit()
        except IntegrityError as exc:
            await _raise_conflict(session, "Budget for this month and category already exists", exc)
        return _budget_to_schema(budget)

    async def _validate_budget_category(
        self,
        user_id: uuid.UUID,
        category_id: uuid.UUID | None,
        session: AsyncSession,
    ) -> uuid.UUID | None:
        if category_id is None:
            return None
        category = await self._get_category_or_404(category_id, session)
        if category.user_id != user_id:
            _raise_not_found("Category not found")
        return category.id

    async def list_monthly_budgets(
        self,
        user_id: uuid.UUID,
        session: AsyncSession,
        year: int | None = None,
        month: int | None = None,
        category_id: uuid.UUID | None = None,
    ) -> list[OutMonthlyBudget]:
        await self._get_user_or_404(user_id, session)
        budgets = await self.repo.list_monthly_budgets(
            user_id=user_id,
            session=session,
            year=year,
            month=month,
            category_id=category_id,
        )
        return [_budget_to_schema(budget) for budget in budgets]

    async def get_monthly_budget(
        self,
        budget_id: uuid.UUID,
        session: AsyncSession,
    ) -> OutMonthlyBudget:
        return _budget_to_schema(await self._get_budget_or_404(budget_id, session))

    async def update_monthly_budget(
        self,
        budget_id: uuid.UUID,
        payload: UpdateMonthlyBudget,
        session: AsyncSession,
    ) -> OutMonthlyBudget:
        budget = await self._get_budget_or_404(budget_id, session)
        data = payload.model_dump(exclude_unset=True)
        target_year = data.get("year", budget.year)
        target_month = data.get("month", budget.month)
        target_category_id = (
            await self._validate_budget_category(budget.user_id, data["category_id"], session)
            if "category_id" in data
            else budget.category_id
        )
        existing = await self.repo.get_monthly_budget(
            user_id=budget.user_id,
            year=target_year,
            month=target_month,
            category_id=target_category_id,
            session=session,
        )
        if existing is not None and existing.id != budget.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Budget for this month and category already exists",
            )

        if "year" in data and data["year"] is not None:
            budget.year = data["year"]
        if "month" in data and data["month"] is not None:
            budget.month = data["month"]
        if "amount" in data and data["amount"] is not None:
            budget.amount = data["amount"]
        if "category_id" in data:
            budget.category_id = target_category_id
        budget.updated_at = datetime.now(timezone.utc)

        try:
            result = await self.repo.save(budget, session)
            await session.commit()
        except IntegrityError as exc:
            await _raise_conflict(session, "Budget for this month and category already exists", exc)
        return _budget_to_schema(result)

    async def delete_monthly_budget(
        self,
        budget_id: uuid.UUID,
        session: AsyncSession,
    ) -> None:
        budget = await self._get_budget_or_404(budget_id, session)
        await self.repo.delete_monthly_budget(budget, session)
        await session.commit()

    async def get_month_analytics(
        self,
        user_id: uuid.UUID,
        year: int | None,
        month: int | None,
        session: AsyncSession,
    ) -> MonthlyAnalytics:
        await self._get_user_or_404(user_id, session)

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
        budget = await self.get_budget_status(user_id, analytics.year, analytics.month, session)
        return _analytics_to_schema(analytics, budget)

    async def get_budget_status(
        self,
        user_id: uuid.UUID,
        year: int | None,
        month: int | None,
        session: AsyncSession,
    ) -> BudgetStatus:
        await self._get_user_or_404(user_id, session)
        start_at, end_at = build_month_period(year=year, month=month)
        expenses = await self.repo.list_expenses(user_id, start_at, end_at, session)
        analytics = build_monthly_analytics(expenses, start_at)
        budgets = await self.repo.list_monthly_budgets(
            user_id=user_id,
            session=session,
            year=analytics.year,
            month=analytics.month,
        )

        total_budget = next((budget for budget in budgets if budget.category_id is None), None)
        budget_amount = to_money(total_budget.amount) if total_budget else None
        spent = analytics.total
        remaining = to_money(budget_amount - spent) if budget_amount is not None else None
        percent_used = (
            to_money(spent / budget_amount * Decimal("100"))
            if budget_amount and budget_amount > 0
            else None
        )

        category_statuses = await self._build_category_budget_statuses(
            budgets=budgets,
            expenses=expenses,
            session=session,
        )

        return BudgetStatus(
            year=analytics.year,
            month=analytics.month,
            budget=budget_amount,
            spent=spent,
            remaining=remaining,
            percent_used=percent_used,
            exceeded=budget_amount is not None and spent > budget_amount,
            category_budgets=category_statuses,
        )

    async def _build_category_budget_statuses(
        self,
        budgets: list[MonthlyBudget],
        expenses: list[Expense],
        session: AsyncSession,
    ) -> list[CategoryBudgetStatus]:
        spent_by_category_id: dict[uuid.UUID, Decimal] = {}
        spent_by_category_name: dict[str, Decimal] = {}
        for expense in expenses:
            amount = to_money(Decimal(expense.amount))
            if expense.category_id is not None:
                spent_by_category_id[expense.category_id] = (
                    spent_by_category_id.get(expense.category_id, Decimal("0")) + amount
                )
            category_name = normalize_category(expense.category)
            spent_by_category_name[category_name] = (
                spent_by_category_name.get(category_name, Decimal("0")) + amount
            )

        statuses: list[CategoryBudgetStatus] = []
        for budget in budgets:
            if budget.category_id is None:
                continue
            category = await self.repo.get_category_by_id(budget.category_id, session)
            category_name = category.name if category else "category"
            spent = spent_by_category_id.get(budget.category_id)
            if spent is None:
                spent = spent_by_category_name.get(category_name, Decimal("0"))
            spent = to_money(spent)
            budget_amount = to_money(budget.amount)
            remaining = to_money(budget_amount - spent)
            statuses.append(
                CategoryBudgetStatus(
                    category_id=budget.category_id,
                    category=category_name,
                    budget=budget_amount,
                    spent=spent,
                    remaining=remaining,
                    percent_used=to_money(spent / budget_amount * Decimal("100")),
                    exceeded=spent > budget_amount,
                )
            )
        return statuses

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

    async def get_telegram_budget_status(
        self,
        telegram_id: int,
        display_name: str | None,
        year: int | None,
        month: int | None,
        session: AsyncSession,
    ) -> BudgetStatus:
        user = await self.get_or_create_telegram_user(telegram_id, display_name, session)
        return await self.get_budget_status(user.id, year, month, session)

    async def list_telegram_categories(
        self,
        telegram_id: int,
        display_name: str | None,
        session: AsyncSession,
    ) -> list[OutCategory]:
        user = await self.get_or_create_telegram_user(telegram_id, display_name, session)
        return await self.list_categories(user.id, session)

    async def create_telegram_category(
        self,
        telegram_id: int,
        display_name: str | None,
        payload: CreateCategory,
        session: AsyncSession,
    ) -> OutCategory:
        user = await self.get_or_create_telegram_user(telegram_id, display_name, session)
        return await self.create_category(user.id, payload, session)

    async def list_telegram_payment_methods(
        self,
        telegram_id: int,
        display_name: str | None,
        session: AsyncSession,
    ) -> list[OutPaymentMethod]:
        user = await self.get_or_create_telegram_user(telegram_id, display_name, session)
        return await self.list_payment_methods(user.id, session)

    async def create_telegram_payment_method(
        self,
        telegram_id: int,
        display_name: str | None,
        payload: CreatePaymentMethod,
        session: AsyncSession,
    ) -> OutPaymentMethod:
        user = await self.get_or_create_telegram_user(telegram_id, display_name, session)
        return await self.create_payment_method(user.id, payload, session)

    async def set_telegram_budget(
        self,
        telegram_id: int,
        display_name: str | None,
        year: int,
        month: int,
        amount: Decimal,
        category_name: str | None,
        session: AsyncSession,
    ) -> OutMonthlyBudget:
        user = await self.get_or_create_telegram_user(telegram_id, display_name, session)
        category_id: uuid.UUID | None = None
        if category_name is not None:
            category = await self._ensure_category_for_user(
                user_id=user.id,
                category_name=category_name,
                session=session,
            )
            category_id = category.id

        existing = await self.repo.get_monthly_budget(
            user_id=user.id,
            year=year,
            month=month,
            category_id=category_id,
            session=session,
        )
        try:
            if existing is None:
                budget = await self.repo.create_monthly_budget(
                    MonthlyBudget(
                        user_id=user.id,
                        category_id=category_id,
                        year=year,
                        month=month,
                        amount=amount,
                    ),
                    session,
                )
            else:
                existing.amount = amount
                existing.updated_at = datetime.now(timezone.utc)
                budget = await self.repo.save(existing, session)
            await session.commit()
        except IntegrityError as exc:
            await _raise_conflict(session, "Budget for this month and category already exists", exc)
        return _budget_to_schema(budget)

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
