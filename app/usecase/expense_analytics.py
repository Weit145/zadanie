from __future__ import annotations

import calendar
import html
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Protocol


MONEY_QUANT = Decimal("0.01")


class ExpenseLike(Protocol):
    amount: Decimal
    category: str
    spent_at: datetime


class BudgetStatusLike(Protocol):
    budget: Decimal | None
    spent: Decimal
    remaining: Decimal | None
    percent_used: Decimal | None
    exceeded: bool


@dataclass(slots=True, frozen=True)
class CategoryTotal:
    category: str
    total: Decimal
    percent: Decimal


@dataclass(slots=True, frozen=True)
class DailyTotal:
    day: int
    total: Decimal


@dataclass(slots=True, frozen=True)
class MonthlyAnalytics:
    year: int
    month: int
    total: Decimal
    count: int
    average_per_expense: Decimal
    average_per_day: Decimal
    categories: tuple[CategoryTotal, ...]
    daily: tuple[DailyTotal, ...]


def to_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def normalize_category(category: str) -> str:
    normalized = " ".join(category.strip().lower().split())
    return normalized or "other"


def build_month_period(
    year: int | None = None,
    month: int | None = None,
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)

    target_year = year or current.year
    target_month = month or current.month
    if target_month < 1 or target_month > 12:
        raise ValueError("month must be between 1 and 12")

    start = datetime(target_year, target_month, 1, tzinfo=timezone.utc)
    if target_month == 12:
        end = datetime(target_year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(target_year, target_month + 1, 1, tzinfo=timezone.utc)
    return start, end


def build_monthly_analytics(
    expenses: Iterable[ExpenseLike],
    start_at: datetime,
) -> MonthlyAnalytics:
    year = start_at.year
    month = start_at.month
    days_count = calendar.monthrange(year, month)[1]
    category_totals: dict[str, Decimal] = {}
    daily_totals: dict[int, Decimal] = {day: Decimal("0") for day in range(1, days_count + 1)}
    total = Decimal("0")
    count = 0

    for expense in expenses:
        amount = to_money(Decimal(expense.amount))
        category = normalize_category(expense.category)
        total += amount
        count += 1
        category_totals[category] = category_totals.get(category, Decimal("0")) + amount
        daily_totals[expense.spent_at.day] = daily_totals.get(expense.spent_at.day, Decimal("0")) + amount

    total = to_money(total)
    categories = tuple(
        CategoryTotal(
            category=category,
            total=to_money(category_total),
            percent=to_money((category_total / total * Decimal("100")) if total else Decimal("0")),
        )
        for category, category_total in sorted(
            category_totals.items(),
            key=lambda item: (-item[1], item[0]),
        )
    )
    daily = tuple(
        DailyTotal(day=day, total=to_money(day_total))
        for day, day_total in sorted(daily_totals.items())
    )

    return MonthlyAnalytics(
        year=year,
        month=month,
        total=total,
        count=count,
        average_per_expense=to_money(total / count) if count else Decimal("0.00"),
        average_per_day=to_money(total / Decimal(days_count)) if days_count else Decimal("0.00"),
        categories=categories,
        daily=daily,
    )


def format_money(value: Decimal) -> str:
    return f"{to_money(value):,.2f}".replace(",", " ")


def build_dashboard_svg(
    analytics: MonthlyAnalytics,
    budget: BudgetStatusLike | None = None,
    width: int = 960,
    height: int = 540,
) -> str:
    chart_x = 64
    chart_y = 286
    chart_width = width - 128
    chart_height = 160
    max_day_total = max((point.total for point in analytics.daily), default=Decimal("0"))
    max_day_total = max(max_day_total, Decimal("1"))
    category_rows = analytics.categories[:6]
    max_category_total = max((item.total for item in category_rows), default=Decimal("1"))
    max_category_total = max(max_category_total, Decimal("1"))

    daily_points: list[str] = []
    daily_count = max(len(analytics.daily) - 1, 1)
    for index, point in enumerate(analytics.daily):
        x = chart_x + (chart_width * index / daily_count)
        y = chart_y + chart_height - (float(point.total / max_day_total) * chart_height)
        daily_points.append(f"{x:.1f},{y:.1f}")

    bars = []
    for index, item in enumerate(category_rows):
        y = 104 + index * 28
        bar_width = int((item.total / max_category_total) * Decimal(390))
        safe_category = html.escape(item.category)
        bars.append(
            f'<text x="64" y="{y + 16}" class="label">{safe_category}</text>'
            f'<rect x="220" y="{y}" width="{bar_width}" height="18" rx="4" class="bar" />'
            f'<text x="{230 + bar_width}" y="{y + 15}" class="value">{format_money(item.total)}</text>'
        )

    if not bars:
        bars.append('<text x="64" y="148" class="muted">No expenses for this month</text>')

    budget_label = "Budget is not set"
    budget_class = "caption"
    if budget and budget.budget is not None:
        budget_label = (
            f"Budget: {format_money(budget.budget)} | "
            f"Remaining: {format_money(budget.remaining or Decimal('0'))} | "
            f"Used: {budget.percent_used or Decimal('0.00')}%"
        )
        if budget.exceeded:
            budget_label = f"Budget exceeded | {budget_label}"
            budget_class = "danger"

    month_name = f"{analytics.month:02d}.{analytics.year}"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Expense dashboard">
<style>
    .bg {{ fill: #f7f4ed; }}
    .panel {{ fill: #ffffff; stroke: #d8d0c3; stroke-width: 1; }}
    .title {{ font: 700 30px Arial, sans-serif; fill: #202124; }}
    .metric {{ font: 700 24px Arial, sans-serif; fill: #0b6b5f; }}
    .caption {{ font: 14px Arial, sans-serif; fill: #5f6368; }}
    .label {{ font: 14px Arial, sans-serif; fill: #2b2b2b; }}
    .value {{ font: 13px Arial, sans-serif; fill: #5f6368; }}
    .muted {{ font: 15px Arial, sans-serif; fill: #80868b; }}
    .danger {{ font: 700 14px Arial, sans-serif; fill: #b42318; }}
    .bar {{ fill: #d84f3a; }}
    .line {{ fill: none; stroke: #0b6b5f; stroke-width: 4; stroke-linejoin: round; stroke-linecap: round; }}
    .axis {{ stroke: #c7bfb4; stroke-width: 1; }}
</style>
<rect class="bg" width="100%" height="100%" />
<text x="48" y="52" class="title">Monthly expenses: {month_name}</text>
<rect x="48" y="72" width="864" height="170" rx="8" class="panel" />
<text x="64" y="102" class="caption">Categories</text>
{"".join(bars)}
<rect x="640" y="96" width="220" height="112" rx="8" fill="#edf7f5" />
<text x="660" y="132" class="caption">Total</text>
<text x="660" y="166" class="metric">{format_money(analytics.total)}</text>
<text x="660" y="192" class="caption">{analytics.count} expense(s), avg {format_money(analytics.average_per_expense)}</text>
<text x="660" y="220" class="{budget_class}">{html.escape(budget_label)}</text>
<text x="48" y="274" class="caption">Daily dynamics</text>
<line x1="{chart_x}" y1="{chart_y + chart_height}" x2="{chart_x + chart_width}" y2="{chart_y + chart_height}" class="axis" />
<polyline points="{" ".join(daily_points)}" class="line" />
<text x="{chart_x}" y="{chart_y + chart_height + 28}" class="caption">1</text>
<text x="{chart_x + chart_width - 24}" y="{chart_y + chart_height + 28}" class="caption">{len(analytics.daily)}</text>
<text x="48" y="512" class="caption">Average per day: {format_money(analytics.average_per_day)}</text>
</svg>"""


def build_dashboard_html(
    analytics: MonthlyAnalytics,
    svg: str,
    budget: BudgetStatusLike | None = None,
) -> str:
    budget_value = "Не задан"
    remaining_value = "Не задан"
    percent_value = "0.00%"
    budget_warning = ""
    budget_class = "metric"
    if budget and budget.budget is not None:
        budget_value = format_money(budget.budget)
        remaining_value = format_money(budget.remaining or Decimal("0"))
        percent_value = f"{budget.percent_used or Decimal('0.00')}%"
        if budget.exceeded:
            budget_warning = "<p class=\"warning\">Бюджет превышен</p>"
            budget_class = "metric warning-box"

    return f"""<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Expense dashboard</title>
    <style>
        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            color: #202124;
            background: #f7f4ed;
        }}
        main {{
            max-width: 1040px;
            margin: 0 auto;
            padding: 28px 18px 40px;
        }}
        h1 {{
            margin: 0 0 18px;
            font-size: 30px;
            font-weight: 700;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            margin-bottom: 18px;
        }}
        .metric {{
            background: #fff;
            border: 1px solid #d8d0c3;
            border-radius: 8px;
            padding: 16px;
        }}
        .metric span {{
            display: block;
            color: #5f6368;
            font-size: 13px;
            margin-bottom: 8px;
        }}
        .metric strong {{
            color: #0b6b5f;
            font-size: 24px;
        }}
        .warning-box {{
            border-color: #fda29b;
            background: #fff5f5;
        }}
        .warning {{
            margin: 0 0 14px;
            color: #b42318;
            font-weight: 700;
        }}
        .chart {{
            overflow-x: auto;
            background: #fff;
            border: 1px solid #d8d0c3;
            border-radius: 8px;
        }}
        svg {{
            display: block;
            width: 100%;
            min-width: 760px;
            height: auto;
        }}
    </style>
</head>
<body>
    <main>
        <h1>Dashboard расходов за {analytics.month:02d}.{analytics.year}</h1>
        {budget_warning}
        <section class="metrics">
            <div class="metric"><span>Всего</span><strong>{format_money(analytics.total)}</strong></div>
            <div class="metric"><span>Операций</span><strong>{analytics.count}</strong></div>
            <div class="metric"><span>Средний расход</span><strong>{format_money(analytics.average_per_expense)}</strong></div>
            <div class="metric"><span>Среднее в день</span><strong>{format_money(analytics.average_per_day)}</strong></div>
            <div class="{budget_class}"><span>Бюджет</span><strong>{budget_value}</strong></div>
            <div class="{budget_class}"><span>Остаток</span><strong>{remaining_value}</strong></div>
            <div class="{budget_class}"><span>Использовано</span><strong>{percent_value}</strong></div>
        </section>
        <section class="chart">{svg}</section>
    </main>
</body>
</html>"""
