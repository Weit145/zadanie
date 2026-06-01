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


@dataclass(slots=True, frozen=True)
class ParsedCategory:
    name: str
    color: str = "#4f46e5"


@dataclass(slots=True, frozen=True)
class ParsedPaymentMethod:
    name: str
    method_type: str = "other"


@dataclass(slots=True, frozen=True)
class ParsedBudget:
    year: int
    month: int
    amount: Decimal
    category: str | None = None


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


def parse_category_args(text: str) -> ParsedCategory:
    payload = _command_payload(text)
    if not payload:
        raise ValueError("Нужно указать категорию: /add_category кафе #ff0000")

    parts = payload.split()
    color = "#4f46e5"
    if parts and re.fullmatch(r"#[0-9a-fA-F]{6}", parts[-1]):
        color = parts[-1].lower()
        parts = parts[:-1]

    name = normalize_category(" ".join(parts))
    if not name:
        raise ValueError("Название категории не должно быть пустым")
    return ParsedCategory(name=name, color=color)


def parse_payment_method_args(text: str) -> ParsedPaymentMethod:
    payload = _command_payload(text)
    if not payload:
        raise ValueError("Нужно указать способ оплаты: /add_payment_method карта")

    parts = payload.split(maxsplit=1)
    name = normalize_category(parts[0])
    method_type = normalize_category(parts[1]) if len(parts) == 2 else "other"
    if not name:
        raise ValueError("Название способа оплаты не должно быть пустым")
    return ParsedPaymentMethod(name=name, method_type=method_type)


def parse_budget_args(text: str) -> ParsedBudget:
    payload = _command_payload(text)
    if not payload:
        raise ValueError("Нужно указать бюджет: /budget 05 2026 20000")

    compact_match = re.fullmatch(
        r"(?:(\d{4})[-./](\d{1,2})|(\d{1,2})[-./](\d{4}))\s+(.+)",
        payload,
    )
    if compact_match:
        year = int(compact_match.group(1) or compact_match.group(4))
        month = int(compact_match.group(2) or compact_match.group(3))
        tail = compact_match.group(5).split()
    else:
        parts = payload.split()
        if len(parts) < 3:
            raise ValueError("Нужно указать месяц, год и сумму бюджета")
        first, second = int(parts[0]), int(parts[1])
        if first > 31:
            year, month = first, second
        else:
            month, year = first, second
        tail = parts[2:]

    _validate_month(month)
    if len(tail) == 1:
        category = None
        raw_amount = tail[0]
    else:
        category = normalize_category(" ".join(tail[:-1]))
        raw_amount = tail[-1]

    amount = _parse_positive_decimal(raw_amount)
    return ParsedBudget(year=year, month=month, amount=amount, category=category)


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


def _command_payload(text: str) -> str:
    parts = text.strip().split(maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else ""


def _parse_positive_decimal(raw_amount: str) -> Decimal:
    try:
        amount = Decimal(raw_amount.replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError("Сумма должна быть числом") from exc

    if amount <= 0:
        raise ValueError("Сумма должна быть больше нуля")
    return amount
