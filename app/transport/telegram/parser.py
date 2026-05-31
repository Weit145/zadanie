from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from app.usecase.expense_analytics import normalize_category


@dataclass(slots=True, frozen=True)
class ParsedExpense:
    amount: Decimal
    category: str
    description: str | None = None


class ExpenseParseError(ValueError):
    pass


def parse_expense_message(text: str) -> ParsedExpense:
    payload = text.strip()
    if payload.lower().startswith("/add"):
        payload = payload.split(maxsplit=1)[1] if len(payload.split(maxsplit=1)) == 2 else ""

    parts = payload.split(maxsplit=2)
    if len(parts) < 2:
        raise ExpenseParseError("Нужно указать сумму и категорию: /add 250 кафе обед")

    raw_amount = parts[0].replace(",", ".")
    try:
        amount = Decimal(raw_amount)
    except InvalidOperation as exc:
        raise ExpenseParseError("Сумма должна быть числом") from exc

    if amount <= 0:
        raise ExpenseParseError("Сумма должна быть больше нуля")

    category = normalize_category(parts[1])
    description = parts[2].strip() if len(parts) == 3 and parts[2].strip() else None
    return ParsedExpense(amount=amount, category=category, description=description)


def parse_month_args(
    text: str,
    now: datetime | None = None,
) -> tuple[int | None, int | None]:
    current = now or datetime.now(timezone.utc)
    command_tail = text.strip().split(maxsplit=1)
    if len(command_tail) == 1:
        return None, None

    payload = command_tail[1].strip()
    if not payload:
        return None, None

    compact_match = re.fullmatch(r"(?:(\d{4})[-./](\d{1,2})|(\d{1,2})[-./](\d{4}))", payload)
    if compact_match:
        year = int(compact_match.group(1) or compact_match.group(4))
        month = int(compact_match.group(2) or compact_match.group(3))
        _validate_month(month)
        return year, month

    parts = payload.split()
    if len(parts) == 1:
        month = int(parts[0])
        _validate_month(month)
        return current.year, month

    first, second = int(parts[0]), int(parts[1])
    if first > 31:
        year, month = first, second
    else:
        month, year = first, second
    _validate_month(month)
    return year, month


def _validate_month(month: int) -> None:
    if month < 1 or month > 12:
        raise ValueError("Месяц должен быть от 1 до 12")
