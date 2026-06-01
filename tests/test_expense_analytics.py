import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.transport.api.v1.schemas.budget import BudgetStatus
from app.usecase.expense_analytics import (
    build_dashboard_html,
    build_dashboard_svg,
    build_month_period,
    build_monthly_analytics,
)


@dataclass(slots=True)
class FakeExpense:
    amount: Decimal
    category: str
    spent_at: datetime


class ExpenseAnalyticsTestCase(unittest.TestCase):
    def test_build_month_period(self) -> None:
        start, end = build_month_period(2026, 5)

        self.assertEqual(start, datetime(2026, 5, 1, tzinfo=timezone.utc))
        self.assertEqual(end, datetime(2026, 6, 1, tzinfo=timezone.utc))

    def test_build_monthly_analytics(self) -> None:
        start, _ = build_month_period(2026, 5)
        expenses = [
            FakeExpense(Decimal("100.00"), "Food", datetime(2026, 5, 1, tzinfo=timezone.utc)),
            FakeExpense(Decimal("50.50"), "food", datetime(2026, 5, 1, tzinfo=timezone.utc)),
            FakeExpense(Decimal("200.00"), "Taxi", datetime(2026, 5, 2, tzinfo=timezone.utc)),
        ]

        analytics = build_monthly_analytics(expenses, start)

        self.assertEqual(analytics.total, Decimal("350.50"))
        self.assertEqual(analytics.count, 3)
        self.assertEqual(analytics.categories[0].category, "taxi")
        self.assertEqual(analytics.categories[0].total, Decimal("200.00"))
        self.assertEqual(analytics.categories[1].category, "food")
        self.assertEqual(analytics.categories[1].total, Decimal("150.50"))
        self.assertEqual(analytics.daily[0].total, Decimal("150.50"))
        self.assertEqual(analytics.daily[1].total, Decimal("200.00"))

    def test_dashboard_svg_escapes_category_names(self) -> None:
        start, _ = build_month_period(2026, 5)
        analytics = build_monthly_analytics(
            [FakeExpense(Decimal("10.00"), "<food>", datetime(2026, 5, 1, tzinfo=timezone.utc))],
            start,
        )

        svg = build_dashboard_svg(analytics)

        self.assertIn("<svg", svg)
        self.assertIn("&lt;food&gt;", svg)
        self.assertNotIn("<food>", svg)

    def test_empty_month(self) -> None:
        start, _ = build_month_period(2026, 5)

        analytics = build_monthly_analytics([], start)

        self.assertEqual(analytics.total, Decimal("0.00"))
        self.assertEqual(analytics.count, 0)
        self.assertEqual(analytics.categories, ())
        self.assertEqual(len(analytics.daily), 31)

    def test_dashboard_html_marks_exceeded_budget(self) -> None:
        start, _ = build_month_period(2026, 5)
        analytics = build_monthly_analytics(
            [FakeExpense(Decimal("150.00"), "food", datetime(2026, 5, 1, tzinfo=timezone.utc))],
            start,
        )
        budget = BudgetStatus(
            year=2026,
            month=5,
            budget=Decimal("100.00"),
            spent=Decimal("150.00"),
            remaining=Decimal("-50.00"),
            percent_used=Decimal("150.00"),
            exceeded=True,
        )

        html = build_dashboard_html(analytics, build_dashboard_svg(analytics, budget), budget)

        self.assertIn("Бюджет превышен", html)
        self.assertIn("150.00%", html)


if __name__ == "__main__":
    unittest.main()
