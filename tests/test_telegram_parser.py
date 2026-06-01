import unittest
from datetime import datetime, timezone
from decimal import Decimal

from app.transport.telegram.parser import (
    ExpenseParseError,
    parse_budget_args,
    parse_expense_message,
    parse_month_args,
)


class TelegramParserTestCase(unittest.TestCase):
    def test_parse_add_command(self) -> None:
        result = parse_expense_message("/add 250.50 cafe lunch")

        self.assertEqual(result.amount, Decimal("250.50"))
        self.assertEqual(result.category, "cafe")
        self.assertEqual(result.description, "lunch")

    def test_parse_plain_expense_with_comma_decimal(self) -> None:
        result = parse_expense_message("99,90 taxi")

        self.assertEqual(result.amount, Decimal("99.90"))
        self.assertEqual(result.category, "taxi")
        self.assertIsNone(result.description)

    def test_parse_add_command_with_bot_name(self) -> None:
        result = parse_expense_message("/add@money_bot 120 food")

        self.assertEqual(result.amount, Decimal("120"))
        self.assertEqual(result.category, "food")

    def test_reject_invalid_expense(self) -> None:
        with self.assertRaises(ExpenseParseError):
            parse_expense_message("/add free cafe")

    def test_reject_negative_expense(self) -> None:
        with self.assertRaises(ExpenseParseError):
            parse_expense_message("/add -10 cafe")

    def test_parse_month_variants(self) -> None:
        now = datetime(2026, 5, 31, tzinfo=timezone.utc)

        self.assertEqual(parse_month_args("/month", now), (None, None))
        self.assertEqual(parse_month_args("/month 04", now), (2026, 4))
        self.assertEqual(parse_month_args("/month 04 2026", now), (2026, 4))
        self.assertEqual(parse_month_args("/month 2026-04", now), (2026, 4))
        self.assertEqual(parse_month_args("/month 04.2026", now), (2026, 4))

    def test_reject_bad_month(self) -> None:
        with self.assertRaises(ValueError):
            parse_month_args("/month 13")

    def test_parse_budget(self) -> None:
        total = parse_budget_args("/budget 05 2026 20000")
        category = parse_budget_args("/budget 05 2026 cafe 5000")

        self.assertEqual(total.month, 5)
        self.assertEqual(total.year, 2026)
        self.assertEqual(total.amount, Decimal("20000"))
        self.assertIsNone(total.category)
        self.assertEqual(category.category, "cafe")
        self.assertEqual(category.amount, Decimal("5000"))


if __name__ == "__main__":
    unittest.main()
