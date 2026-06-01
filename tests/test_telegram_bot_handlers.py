import unittest
from dataclasses import dataclass
from decimal import Decimal

from app.transport.telegram import bot as bot_module
from app.transport.telegram.bot import ExpenseBot


class FakeTelegramClient:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []
        self.documents: list[dict] = []

    async def send_message(self, chat_id: int, text: str) -> None:
        self.messages.append((chat_id, text))

    async def send_document(
        self,
        chat_id: int,
        filename: str,
        content: bytes,
        caption: str | None = None,
    ) -> None:
        self.documents.append(
            {
                "chat_id": chat_id,
                "filename": filename,
                "content": content,
                "caption": caption,
            }
        )


class FakeTransaction:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None


class FakeDbHelper:
    def transaction(self) -> FakeTransaction:
        return FakeTransaction()


@dataclass(slots=True)
class FakeExpense:
    amount: Decimal
    category: str


class FakeBotService:
    def __init__(self) -> None:
        self.created_expenses: list[dict] = []

    async def get_or_create_telegram_user(self, telegram_id, display_name, session):
        return object()

    async def create_telegram_expense(
        self,
        telegram_id,
        display_name,
        expense,
        session,
    ) -> FakeExpense:
        self.created_expenses.append(
            {
                "telegram_id": telegram_id,
                "display_name": display_name,
                "expense": expense,
            }
        )
        return FakeExpense(amount=expense.amount, category=expense.category)


class TelegramBotHandlersTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.original_service = bot_module.service
        self.original_db_helper = bot_module.db_helper
        self.fake_service = FakeBotService()
        bot_module.service = self.fake_service
        bot_module.db_helper = FakeDbHelper()
        self.client = FakeTelegramClient()
        self.bot = ExpenseBot(self.client)

    async def asyncTearDown(self) -> None:
        bot_module.service = self.original_service
        bot_module.db_helper = self.original_db_helper

    async def test_help_command_uses_mock_telegram_client(self) -> None:
        await self.bot.handle_update(_message_update("/help"))

        self.assertEqual(self.client.messages[0][0], 123)
        self.assertIn("/add 250 кафе обед", self.client.messages[0][1])
        self.assertIn("/budget_status", self.client.messages[0][1])

    async def test_add_command_creates_expense_without_real_telegram_api(self) -> None:
        await self.bot.handle_update(_message_update("/add 250 кафе обед"))

        self.assertEqual(len(self.fake_service.created_expenses), 1)
        created = self.fake_service.created_expenses[0]
        self.assertEqual(created["telegram_id"], 456)
        self.assertEqual(created["expense"].amount, Decimal("250"))
        self.assertEqual(created["expense"].category, "кафе")
        self.assertIn("Добавил", self.client.messages[0][1])


def _message_update(text: str) -> dict:
    return {
        "update_id": 1,
        "message": {
            "chat": {"id": 123},
            "from": {
                "id": 456,
                "username": "tester",
            },
            "text": text,
        },
    }
