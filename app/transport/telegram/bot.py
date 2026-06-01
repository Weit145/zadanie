from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from typing import Any

from fastapi import HTTPException

from app.core.config import settings
from app.core.logging import setup_logging
from app.repositories.storage.postgres.db_helper import db_helper
from app.transport.api.v1.schemas.category import CreateCategory
from app.transport.api.v1.schemas.expense import CreateExpense
from app.transport.api.v1.schemas.payment_method import CreatePaymentMethod
from app.transport.telegram.client import TelegramClient
from app.transport.telegram.parser import (
    ExpenseParseError,
    parse_budget_args,
    parse_category_args,
    parse_expense_message,
    parse_month_args,
    parse_payment_method_args,
)
from app.usecase.expense_analytics import (
    build_dashboard_svg,
    format_money,
)
from app.usecase.service import service


logger = logging.getLogger(__name__)


HELP_TEXT = """Команды:
/add 250 кафе обед - добавить расход
250 кафе обед - добавить расход без команды
/month - итоги текущего месяца
/month 05 2026 - итоги за месяц
/dashboard - SVG-график за месяц
/delete_last - удалить последний расход
/categories - показать категории
/add_category кафе #ff0000 - добавить категорию
/payment_methods - показать способы оплаты
/add_payment_method карта - добавить способ оплаты
/budget 05 2026 20000 - задать общий бюджет
/budget 05 2026 кафе 5000 - задать бюджет категории
/budget_status - статус бюджета текущего месяца
/budget_status 05 2026 - статус бюджета за месяц
/help - помощь"""


class ExpenseBot:
    def __init__(self, client: TelegramClient):
        self.client = client

    async def run(self) -> None:
        offset: int | None = None
        logger.info("Telegram bot started")
        while True:
            try:
                updates = await self.client.get_updates(offset=offset)
                for update in updates:
                    offset = int(update["update_id"]) + 1
                    await self.handle_update(update)
            except Exception:
                logger.exception("Telegram polling error")
                await asyncio.sleep(3)

    async def handle_update(self, update: dict[str, Any]) -> None:
        message = update.get("message")
        if not message or "text" not in message:
            return

        chat_id = int(message["chat"]["id"])
        text = str(message["text"]).strip()
        telegram_user = message.get("from") or {}
        telegram_id = int(telegram_user["id"])
        display_name = _display_name(telegram_user)
        command = _command(text)

        try:
            if command in {"/start", "/help"}:
                await self._handle_start(chat_id, telegram_id, display_name)
            elif command == "/month":
                await self._handle_month(chat_id, telegram_id, display_name, text)
            elif command in {"/dashboard", "/chart"}:
                await self._handle_dashboard(chat_id, telegram_id, display_name, text)
            elif command == "/delete_last":
                await self._handle_delete_last(chat_id, telegram_id, display_name)
            elif command == "/categories":
                await self._handle_categories(chat_id, telegram_id, display_name)
            elif command == "/add_category":
                await self._handle_add_category(chat_id, telegram_id, display_name, text)
            elif command == "/payment_methods":
                await self._handle_payment_methods(chat_id, telegram_id, display_name)
            elif command == "/add_payment_method":
                await self._handle_add_payment_method(chat_id, telegram_id, display_name, text)
            elif command == "/budget":
                await self._handle_budget(chat_id, telegram_id, display_name, text)
            elif command == "/budget_status":
                await self._handle_budget_status(chat_id, telegram_id, display_name, text)
            else:
                await self._handle_add(chat_id, telegram_id, display_name, text)
        except ExpenseParseError as exc:
            await self.client.send_message(chat_id, f"Не понял расход: {exc}")
        except ValueError as exc:
            await self.client.send_message(chat_id, f"Проверь команду: {exc}")
        except HTTPException as exc:
            await self.client.send_message(chat_id, f"Ошибка: {exc.detail}")

    async def _handle_start(
        self,
        chat_id: int,
        telegram_id: int,
        display_name: str,
    ) -> None:
        async with db_helper.transaction() as session:
            await service.get_or_create_telegram_user(telegram_id, display_name, session)
        await self.client.send_message(chat_id, "Готов вести расходы.\n\n" + HELP_TEXT)

    async def _handle_add(
        self,
        chat_id: int,
        telegram_id: int,
        display_name: str,
        text: str,
    ) -> None:
        parsed = parse_expense_message(text)
        async with db_helper.transaction() as session:
            expense = await service.create_telegram_expense(
                telegram_id=telegram_id,
                display_name=display_name,
                expense=CreateExpense(
                    amount=parsed.amount,
                    category=parsed.category,
                    description=parsed.description,
                ),
                session=session,
            )
        await self.client.send_message(
            chat_id,
            f"Добавил: {format_money(expense.amount)} в категории «{expense.category}».",
        )

    async def _handle_month(
        self,
        chat_id: int,
        telegram_id: int,
        display_name: str,
        text: str,
    ) -> None:
        year, month = parse_month_args(text)
        async with db_helper.transaction() as session:
            analytics = await service.get_telegram_month_analytics(
                telegram_id=telegram_id,
                display_name=display_name,
                year=year,
                month=month,
                session=session,
            )
        lines = [
            f"Итоги за {analytics.month:02d}.{analytics.year}",
            f"Всего: {format_money(analytics.total)}",
            f"Операций: {analytics.count}",
            f"Среднее в день: {format_money(analytics.average_per_day)}",
        ]
        if analytics.categories:
            lines.append("")
            lines.extend(
                f"{item.category}: {format_money(item.total)} ({item.percent}%)"
                for item in analytics.categories[:8]
            )
        await self.client.send_message(chat_id, "\n".join(lines))

    async def _handle_dashboard(
        self,
        chat_id: int,
        telegram_id: int,
        display_name: str,
        text: str,
    ) -> None:
        year, month = parse_month_args(text)
        async with db_helper.transaction() as session:
            analytics = await service.get_telegram_month_analytics(
                telegram_id=telegram_id,
                display_name=display_name,
                year=year,
                month=month,
                session=session,
            )
            budget = await service.get_telegram_budget_status(
                telegram_id=telegram_id,
                display_name=display_name,
                year=analytics.year,
                month=analytics.month,
                session=session,
            )
        svg = build_dashboard_svg(analytics, budget).encode("utf-8")
        await self.client.send_document(
            chat_id=chat_id,
            filename=f"expenses-{analytics.year}-{analytics.month:02d}.svg",
            content=svg,
            caption=f"Dashboard за {analytics.month:02d}.{analytics.year}",
        )

    async def _handle_delete_last(
        self,
        chat_id: int,
        telegram_id: int,
        display_name: str,
    ) -> None:
        async with db_helper.transaction() as session:
            deleted = await service.delete_last_telegram_expense(
                telegram_id=telegram_id,
                display_name=display_name,
                session=session,
            )
        if deleted is None:
            await self.client.send_message(chat_id, "Пока нечего удалять.")
            return
        await self.client.send_message(
            chat_id,
            f"Удалил: {format_money(deleted.amount)} в категории «{deleted.category}».",
        )

    async def _handle_categories(
        self,
        chat_id: int,
        telegram_id: int,
        display_name: str,
    ) -> None:
        async with db_helper.transaction() as session:
            categories = await service.list_telegram_categories(telegram_id, display_name, session)
        if not categories:
            await self.client.send_message(chat_id, "Категорий пока нет.")
            return
        lines = ["Категории:"]
        lines.extend(f"{item.name} {item.color}" for item in categories)
        await self.client.send_message(chat_id, "\n".join(lines))

    async def _handle_add_category(
        self,
        chat_id: int,
        telegram_id: int,
        display_name: str,
        text: str,
    ) -> None:
        parsed = parse_category_args(text)
        async with db_helper.transaction() as session:
            category = await service.create_telegram_category(
                telegram_id=telegram_id,
                display_name=display_name,
                payload=CreateCategory(name=parsed.name, color=parsed.color),
                session=session,
            )
        await self.client.send_message(
            chat_id,
            f"Добавил категорию «{category.name}» {category.color}.",
        )

    async def _handle_payment_methods(
        self,
        chat_id: int,
        telegram_id: int,
        display_name: str,
    ) -> None:
        async with db_helper.transaction() as session:
            methods = await service.list_telegram_payment_methods(
                telegram_id,
                display_name,
                session,
            )
        if not methods:
            await self.client.send_message(chat_id, "Способов оплаты пока нет.")
            return
        lines = ["Способы оплаты:"]
        lines.extend(f"{item.name} ({item.method_type})" for item in methods)
        await self.client.send_message(chat_id, "\n".join(lines))

    async def _handle_add_payment_method(
        self,
        chat_id: int,
        telegram_id: int,
        display_name: str,
        text: str,
    ) -> None:
        parsed = parse_payment_method_args(text)
        async with db_helper.transaction() as session:
            method = await service.create_telegram_payment_method(
                telegram_id=telegram_id,
                display_name=display_name,
                payload=CreatePaymentMethod(
                    name=parsed.name,
                    method_type=parsed.method_type,
                ),
                session=session,
            )
        await self.client.send_message(
            chat_id,
            f"Добавил способ оплаты «{method.name}» ({method.method_type}).",
        )

    async def _handle_budget(
        self,
        chat_id: int,
        telegram_id: int,
        display_name: str,
        text: str,
    ) -> None:
        parsed = parse_budget_args(text)
        async with db_helper.transaction() as session:
            budget = await service.set_telegram_budget(
                telegram_id=telegram_id,
                display_name=display_name,
                year=parsed.year,
                month=parsed.month,
                amount=parsed.amount,
                category_name=parsed.category,
                session=session,
            )
        target = "общий бюджет" if budget.category_id is None else f"бюджет «{parsed.category}»"
        await self.client.send_message(
            chat_id,
            f"Задал {target} на {budget.month:02d}.{budget.year}: {format_money(budget.amount)}.",
        )

    async def _handle_budget_status(
        self,
        chat_id: int,
        telegram_id: int,
        display_name: str,
        text: str,
    ) -> None:
        year, month = parse_month_args(text)
        async with db_helper.transaction() as session:
            budget = await service.get_telegram_budget_status(
                telegram_id=telegram_id,
                display_name=display_name,
                year=year,
                month=month,
                session=session,
            )
        lines = [
            f"Бюджет за {budget.month:02d}.{budget.year}",
            f"Потрачено: {format_money(budget.spent)}",
        ]
        if budget.budget is None:
            lines.append("Общий бюджет не задан.")
        else:
            lines.extend(
                [
                    f"Лимит: {format_money(budget.budget)}",
                    f"Остаток: {format_money(budget.remaining or Decimal('0'))}",
                    f"Использовано: {budget.percent_used or 0}%",
                ]
            )
            if budget.exceeded:
                lines.append("Бюджет превышен.")
        if budget.category_budgets:
            lines.append("")
            lines.extend(
                (
                    f"{item.category}: {format_money(item.spent)} / {format_money(item.budget)} "
                    f"({item.percent_used}%)"
                )
                for item in budget.category_budgets[:8]
            )
        await self.client.send_message(chat_id, "\n".join(lines))


def _display_name(telegram_user: dict[str, Any]) -> str:
    if telegram_user.get("username"):
        return str(telegram_user["username"])
    return " ".join(
        part
        for part in [
            str(telegram_user.get("first_name") or "").strip(),
            str(telegram_user.get("last_name") or "").strip(),
        ]
        if part
    ) or "telegram"


def _command(text: str) -> str:
    if not text.startswith("/"):
        return ""
    command = text.split(maxsplit=1)[0]
    return command.split("@", maxsplit=1)[0].lower()


async def run_bot() -> None:
    setup_logging()
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    client = TelegramClient(
        token=settings.telegram_bot_token,
        timeout=settings.telegram_poll_timeout,
    )
    await ExpenseBot(client).run()


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
