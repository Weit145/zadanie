import json
import unittest
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import ModuleType
from urllib.parse import urlsplit

from fastapi import HTTPException, status

from app.main import app
from app.repositories.storage.postgres.db_helper import db_helper
from app.transport.api.v1.handler import (
    budgets,
    categories,
    expenses,
    payment_methods,
    users,
)
from app.transport.api.v1.schemas.budget import (
    BudgetStatus,
    CreateMonthlyBudget,
    OutMonthlyBudget,
)
from app.transport.api.v1.schemas.category import CreateCategory, OutCategory
from app.transport.api.v1.schemas.expense import CreateExpense, Dashboard, OutExpense
from app.transport.api.v1.schemas.payment_method import CreatePaymentMethod, OutPaymentMethod
from app.transport.api.v1.schemas.user import CreateUser, OutUser, UpdateUser
from app.usecase.expense_analytics import (
    build_month_period,
    build_monthly_analytics,
    normalize_category,
    to_money,
)


class FakeApiService:
    def __init__(self) -> None:
        self.users: dict[uuid.UUID, OutUser] = {}
        self.categories: dict[uuid.UUID, OutCategory] = {}
        self.payment_methods: dict[uuid.UUID, OutPaymentMethod] = {}
        self.budgets: dict[uuid.UUID, OutMonthlyBudget] = {}
        self.expenses: dict[uuid.UUID, OutExpense] = {}

    async def create_user(self, payload: CreateUser, session) -> OutUser:
        now = _now()
        user = OutUser(
            id=uuid.uuid4(),
            name=payload.name,
            telegram_id=payload.telegram_id,
            created_at=now,
            updated_at=now,
        )
        self.users[user.id] = user
        return user

    async def list_users(self, session, limit: int = 100, offset: int = 0) -> list[OutUser]:
        return list(self.users.values())[offset : offset + limit]

    async def get_user(self, user_id: uuid.UUID, session) -> OutUser:
        if user_id not in self.users:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return self.users[user_id]

    async def update_user(self, user_id: uuid.UUID, payload: UpdateUser, session) -> OutUser:
        user = await self.get_user(user_id, session)
        data = payload.model_dump(exclude_unset=True)
        updated = user.model_copy(
            update={
                "name": data.get("name", user.name),
                "telegram_id": data.get("telegram_id", user.telegram_id),
                "updated_at": _now(),
            }
        )
        self.users[user_id] = updated
        return updated

    async def delete_user(self, user_id: uuid.UUID, session) -> None:
        await self.get_user(user_id, session)
        del self.users[user_id]

    async def create_category(
        self,
        user_id: uuid.UUID,
        payload: CreateCategory,
        session,
    ) -> OutCategory:
        await self.get_user(user_id, session)
        now = _now()
        name = normalize_category(payload.name)
        if any(
            item.user_id == user_id and item.name == name
            for item in self.categories.values()
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category with this name already exists",
            )
        category = OutCategory(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name,
            color=payload.color.lower(),
            created_at=now,
            updated_at=now,
        )
        self.categories[category.id] = category
        return category

    async def list_categories(self, user_id: uuid.UUID, session) -> list[OutCategory]:
        await self.get_user(user_id, session)
        return [item for item in self.categories.values() if item.user_id == user_id]

    async def get_category(self, category_id: uuid.UUID, session) -> OutCategory:
        if category_id not in self.categories:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        return self.categories[category_id]

    async def update_category(self, category_id: uuid.UUID, payload, session) -> OutCategory:
        category = await self.get_category(category_id, session)
        data = payload.model_dump(exclude_unset=True)
        updated = category.model_copy(
            update={
                "name": normalize_category(data.get("name", category.name)),
                "color": data.get("color", category.color).lower(),
                "updated_at": _now(),
            }
        )
        self.categories[category_id] = updated
        return updated

    async def delete_category(self, category_id: uuid.UUID, session) -> None:
        await self.get_category(category_id, session)
        del self.categories[category_id]

    async def create_payment_method(
        self,
        user_id: uuid.UUID,
        payload: CreatePaymentMethod,
        session,
    ) -> OutPaymentMethod:
        await self.get_user(user_id, session)
        now = _now()
        method = OutPaymentMethod(
            id=uuid.uuid4(),
            user_id=user_id,
            name=normalize_category(payload.name),
            method_type=normalize_category(payload.method_type),
            created_at=now,
            updated_at=now,
        )
        self.payment_methods[method.id] = method
        return method

    async def list_payment_methods(self, user_id: uuid.UUID, session) -> list[OutPaymentMethod]:
        await self.get_user(user_id, session)
        return [item for item in self.payment_methods.values() if item.user_id == user_id]

    async def get_payment_method(self, payment_method_id: uuid.UUID, session) -> OutPaymentMethod:
        if payment_method_id not in self.payment_methods:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment method not found")
        return self.payment_methods[payment_method_id]

    async def update_payment_method(self, payment_method_id: uuid.UUID, payload, session) -> OutPaymentMethod:
        method = await self.get_payment_method(payment_method_id, session)
        data = payload.model_dump(exclude_unset=True)
        updated = method.model_copy(
            update={
                "name": normalize_category(data.get("name", method.name)),
                "method_type": normalize_category(data.get("method_type", method.method_type)),
                "updated_at": _now(),
            }
        )
        self.payment_methods[payment_method_id] = updated
        return updated

    async def delete_payment_method(self, payment_method_id: uuid.UUID, session) -> None:
        await self.get_payment_method(payment_method_id, session)
        del self.payment_methods[payment_method_id]

    async def create_monthly_budget(
        self,
        user_id: uuid.UUID,
        payload: CreateMonthlyBudget,
        session,
    ) -> OutMonthlyBudget:
        await self.get_user(user_id, session)
        now = _now()
        budget = OutMonthlyBudget(
            id=uuid.uuid4(),
            user_id=user_id,
            category_id=payload.category_id,
            year=payload.year,
            month=payload.month,
            amount=payload.amount,
            created_at=now,
            updated_at=now,
        )
        self.budgets[budget.id] = budget
        return budget

    async def list_monthly_budgets(
        self,
        user_id: uuid.UUID,
        session,
        year: int | None = None,
        month: int | None = None,
        category_id: uuid.UUID | None = None,
    ) -> list[OutMonthlyBudget]:
        await self.get_user(user_id, session)
        return [
            item
            for item in self.budgets.values()
            if item.user_id == user_id
            and (year is None or item.year == year)
            and (month is None or item.month == month)
            and (category_id is None or item.category_id == category_id)
        ]

    async def get_monthly_budget(self, budget_id: uuid.UUID, session) -> OutMonthlyBudget:
        if budget_id not in self.budgets:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
        return self.budgets[budget_id]

    async def update_monthly_budget(self, budget_id: uuid.UUID, payload, session) -> OutMonthlyBudget:
        budget = await self.get_monthly_budget(budget_id, session)
        data = payload.model_dump(exclude_unset=True)
        updated = budget.model_copy(update={**data, "updated_at": _now()})
        self.budgets[budget_id] = updated
        return updated

    async def delete_monthly_budget(self, budget_id: uuid.UUID, session) -> None:
        await self.get_monthly_budget(budget_id, session)
        del self.budgets[budget_id]

    async def create_expense(
        self,
        user_id: uuid.UUID,
        payload: CreateExpense,
        session,
    ) -> OutExpense:
        await self.get_user(user_id, session)
        now = _now()
        category = normalize_category(payload.category or "category")
        expense = OutExpense(
            id=uuid.uuid4(),
            user_id=user_id,
            category_id=payload.category_id,
            payment_method_id=payload.payment_method_id,
            amount=payload.amount,
            category=category,
            description=payload.description,
            spent_at=payload.spent_at or now,
            created_at=now,
            updated_at=now,
        )
        self.expenses[expense.id] = expense
        return expense

    async def list_month_expenses(
        self,
        user_id: uuid.UUID,
        year: int | None,
        month: int | None,
        session,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[OutExpense]:
        await self.get_user(user_id, session)
        items = [item for item in self.expenses.values() if item.user_id == user_id]
        if start_at is not None or end_at is not None:
            start = start_at
            end = end_at
        else:
            start, end = build_month_period(year, month)
        return [
            item
            for item in items
            if (start is None or item.spent_at >= start)
            and (end is None or item.spent_at < end)
        ]

    async def get_expense(self, expense_id: uuid.UUID, session) -> OutExpense:
        if expense_id not in self.expenses:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
        return self.expenses[expense_id]

    async def update_expense(self, expense_id: uuid.UUID, payload, session) -> OutExpense:
        expense = await self.get_expense(expense_id, session)
        data = payload.model_dump(exclude_unset=True)
        updated = expense.model_copy(update={**data, "updated_at": _now()})
        self.expenses[expense_id] = updated
        return updated

    async def delete_expense(self, expense_id: uuid.UUID, session) -> None:
        await self.get_expense(expense_id, session)
        del self.expenses[expense_id]

    async def get_month_analytics(self, user_id: uuid.UUID, year: int | None, month: int | None, session):
        await self.get_user(user_id, session)
        start_at, end_at = build_month_period(year, month)
        return build_monthly_analytics(
            [
                item
                for item in self.expenses.values()
                if item.user_id == user_id and start_at <= item.spent_at < end_at
            ],
            start_at,
        )

    async def get_budget_status(
        self,
        user_id: uuid.UUID,
        year: int | None,
        month: int | None,
        session,
    ) -> BudgetStatus:
        analytics = await self.get_month_analytics(user_id, year, month, session)
        total_budget = next(
            (
                item
                for item in self.budgets.values()
                if item.user_id == user_id
                and item.category_id is None
                and item.year == analytics.year
                and item.month == analytics.month
            ),
            None,
        )
        budget_amount = total_budget.amount if total_budget else None
        remaining = to_money(budget_amount - analytics.total) if budget_amount else None
        return BudgetStatus(
            year=analytics.year,
            month=analytics.month,
            budget=budget_amount,
            spent=analytics.total,
            remaining=remaining,
            percent_used=to_money(analytics.total / budget_amount * Decimal("100")) if budget_amount else None,
            exceeded=budget_amount is not None and analytics.total > budget_amount,
        )

    async def get_month_dashboard(self, user_id: uuid.UUID, year: int | None, month: int | None, session) -> Dashboard:
        analytics = await self.get_month_analytics(user_id, year, month, session)
        budget = await self.get_budget_status(user_id, analytics.year, analytics.month, session)
        return Dashboard(
            year=analytics.year,
            month=analytics.month,
            total=analytics.total,
            count=analytics.count,
            average_per_expense=analytics.average_per_expense,
            average_per_day=analytics.average_per_day,
            categories=[
                {"category": item.category, "total": item.total, "percent": item.percent}
                for item in analytics.categories
            ],
            daily=[{"day": item.day, "total": item.total} for item in analytics.daily],
            budget=budget,
        )


class ApiCrudTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.fake_service = FakeApiService()
        self.modules: list[ModuleType] = [users, categories, payment_methods, budgets, expenses]
        self.original_services = {module: module.service for module in self.modules}
        for module in self.modules:
            module.service = self.fake_service

        async def override_session():
            yield object()

        app.dependency_overrides[db_helper.get_session] = override_session

    async def asyncTearDown(self) -> None:
        for module, original in self.original_services.items():
            module.service = original
        app.dependency_overrides.clear()

    async def test_api_crud_flow(self) -> None:
        user_response = await asgi_request(
            "POST",
            "/users",
            json_body={"name": "demo", "telegram_id": 1001},
        )
        self.assertEqual(user_response.status_code, 201)
        user = user_response.json()
        user_id = user["id"]

        users_response = await asgi_request("GET", "/users")
        self.assertEqual(users_response.status_code, 200)
        self.assertEqual(len(users_response.json()), 1)

        get_user_response = await asgi_request("GET", f"/users/{user_id}")
        self.assertEqual(get_user_response.status_code, 200)
        self.assertEqual(get_user_response.json()["name"], "demo")

        patch_user_response = await asgi_request(
            "PATCH",
            f"/users/{user_id}",
            json_body={"name": "demo-updated"},
        )
        self.assertEqual(patch_user_response.status_code, 200)
        self.assertEqual(patch_user_response.json()["name"], "demo-updated")

        category_response = await asgi_request(
            "POST",
            f"/users/{user_id}/categories",
            json_body={"name": "Cafe", "color": "#ff0000"},
        )
        self.assertEqual(category_response.status_code, 201)
        category = category_response.json()
        self.assertEqual(category["name"], "cafe")

        categories_response = await asgi_request("GET", f"/users/{user_id}/categories")
        self.assertEqual(categories_response.status_code, 200)
        self.assertEqual(len(categories_response.json()), 1)

        patch_category_response = await asgi_request(
            "PATCH",
            f"/categories/{category['id']}",
            json_body={"color": "#00ff00"},
        )
        self.assertEqual(patch_category_response.status_code, 200)
        self.assertEqual(patch_category_response.json()["color"], "#00ff00")

        method_response = await asgi_request(
            "POST",
            f"/users/{user_id}/payment-methods",
            json_body={"name": "Card", "method_type": "card"},
        )
        self.assertEqual(method_response.status_code, 201)
        method = method_response.json()

        budget_response = await asgi_request(
            "POST",
            f"/users/{user_id}/budgets",
            json_body={"year": 2026, "month": 5, "amount": "1000.00"},
        )
        self.assertEqual(budget_response.status_code, 201)

        expense_response = await asgi_request(
            "POST",
            f"/users/{user_id}/expenses",
            json_body={
                "amount": "250.50",
                "category": "Cafe",
                "description": "lunch",
                "payment_method_id": method["id"],
                "spent_at": "2026-05-02T12:00:00+00:00",
            },
        )
        self.assertEqual(expense_response.status_code, 201)
        expense = expense_response.json()
        self.assertEqual(expense["category"], "cafe")

        self.assertEqual((await asgi_request("GET", f"/expenses/{expense['id']}")).status_code, 200)
        self.assertEqual(
            (await asgi_request("GET", f"/users/{user_id}/expenses?year=2026&month=5")).status_code,
            200,
        )

        dashboard_response = await asgi_request("GET", f"/users/{user_id}/dashboard?year=2026&month=5")
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertEqual(dashboard_response.json()["count"], 1)

        html_response = await asgi_request("GET", f"/users/{user_id}/dashboard.html?year=2026&month=5")
        self.assertEqual(html_response.status_code, 200)
        self.assertIn("Dashboard", html_response.text)

        svg_response = await asgi_request("GET", f"/users/{user_id}/dashboard.svg?year=2026&month=5")
        self.assertEqual(svg_response.status_code, 200)
        self.assertIn("<svg", svg_response.text)

        delete_expense_response = await asgi_request("DELETE", f"/expenses/{expense['id']}")
        self.assertEqual(delete_expense_response.status_code, 204)

    async def test_api_errors(self) -> None:
        missing_response = await asgi_request("GET", f"/users/{uuid.uuid4()}")
        self.assertEqual(missing_response.status_code, 404)

        user_response = await asgi_request("POST", "/users", json_body={"name": "errors"})
        user_id = user_response.json()["id"]

        invalid_expense_response = await asgi_request(
            "POST",
            f"/users/{user_id}/expenses",
            json_body={"amount": "-1", "category": "cafe"},
        )
        self.assertEqual(invalid_expense_response.status_code, 422)

        invalid_month_response = await asgi_request(
            "GET",
            f"/users/{user_id}/expenses?year=2026&month=13",
        )
        self.assertEqual(invalid_month_response.status_code, 422)

        empty_category_response = await asgi_request(
            "POST",
            f"/users/{user_id}/categories",
            json_body={"name": "   ", "color": "#ff0000"},
        )
        self.assertEqual(empty_category_response.status_code, 422)

        first_category_response = await asgi_request(
            "POST",
            f"/users/{user_id}/categories",
            json_body={"name": "cafe", "color": "#ff0000"},
        )
        self.assertEqual(first_category_response.status_code, 201)
        duplicate_category_response = await asgi_request(
            "POST",
            f"/users/{user_id}/categories",
            json_body={"name": "Cafe", "color": "#00ff00"},
        )
        self.assertEqual(duplicate_category_response.status_code, 409)

        missing_expense_response = await asgi_request("GET", f"/expenses/{uuid.uuid4()}")
        self.assertEqual(missing_expense_response.status_code, 404)


class AsgiResponse:
    def __init__(self, status_code: int, body: bytes, headers: list[tuple[bytes, bytes]]) -> None:
        self.status_code = status_code
        self.body = body
        self.headers = headers
        self.text = body.decode("utf-8")

    def json(self):
        return json.loads(self.text)


async def asgi_request(
    method: str,
    path: str,
    json_body: dict | None = None,
) -> AsgiResponse:
    parsed = urlsplit(path)
    body = json.dumps(json_body).encode("utf-8") if json_body is not None else b""
    headers = [(b"host", b"testserver")]
    if json_body is not None:
        headers.append((b"content-type", b"application/json"))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode("ascii"),
        "query_string": parsed.query.encode("ascii"),
        "headers": headers,
        "client": ("127.0.0.1", 123),
        "server": ("testserver", 80),
    }
    messages = []
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    body_parts = [
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    ]
    return AsgiResponse(start["status"], b"".join(body_parts), start.get("headers", []))


def _now() -> datetime:
    return datetime.now(timezone.utc)
