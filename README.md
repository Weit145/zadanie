# Telegram expense tracker

Telegram-бот и FastAPI-приложение для учета расходов за месяц. Пользователь добавляет траты через бота или REST API, данные хранятся в PostgreSQL, а API отдает расходы, бюджетный статус, JSON/SVG/HTML dashboard.

Тема итоговой работы: разработка телеграм-бота для отслеживания потраченных за месяц денег с функцией графического представления информации и аналитическим дашбордом.

## Стек

- Python 3.12+
- FastAPI
- SQLAlchemy async
- PostgreSQL
- Alembic
- Poetry
- Docker Compose
- pytest
- Uvicorn
- Pydantic
- HTML/SVG

## Архитектура

Проект разделен на транспортный слой, сервисный слой, слой репозиториев и слой хранения данных.

```text
Telegram-пользователь
        ↓
Telegram-бот
        ↓
Service
        ↓
SQLAlchemyRepository
        ↓
PostgreSQL

FastAPI
  ↓
Service
  ↓
SQLAlchemyRepository
  ↓
PostgreSQL

Dashboard JSON/HTML/SVG
  ↓
expense_analytics.py
  ↓
Расходы, категории и бюджеты
```

## Модули

```text
app/core/                 настройки и логирование
app/domain/               доменные dataclass-сущности
app/repositories/         SQLAlchemy-модели и репозиторий
app/transport/api/        REST API handlers и Pydantic-схемы
app/transport/telegram/   Telegram polling client, parser, bot
app/usecase/              сервисный слой, аналитика, dashboard
migrations/               Alembic-миграции
tests/                    unit, API и service-тесты
```

## Командная работа

Проект подходит для выполнения двумя студентами. Логичное распределение:

- первый участник: PostgreSQL, SQLAlchemy-модели, Alembic-миграции, репозитории, FastAPI CRUD, Docker;
- второй участник: Telegram-бот, парсинг команд, аналитика расходов, JSON/HTML/SVG dashboard, тесты, README и демонстрация.

## База данных

В проекте используются связанные таблицы:

- `user`: `id`, `name`, `telegram_id`, `created_at`, `updated_at`.
- `expense`: `id`, `user_id`, `category_id`, `payment_method_id`, `amount`, `category`, `description`, `spent_at`, `created_at`, `updated_at`.
- `category`: `id`, `user_id`, `name`, `color`, `created_at`, `updated_at`; категория уникальна в пределах пользователя.
- `payment_method`: `id`, `user_id`, `name`, `method_type`, `created_at`, `updated_at`.
- `monthly_budget`: `id`, `user_id`, `category_id`, `year`, `month`, `amount`, `created_at`, `updated_at`; поддерживает общий бюджет и бюджет по категории.

## API

Swagger доступен по адресу:

```text
http://localhost:8000/docs
```

CRUD endpoints:

```text
POST   /users
GET    /users
GET    /users/{user_id}
PATCH  /users/{user_id}
DELETE /users/{user_id}

POST   /users/{user_id}/expenses
GET    /users/{user_id}/expenses
GET    /expenses/{expense_id}
PATCH  /expenses/{expense_id}
DELETE /expenses/{expense_id}

POST   /users/{user_id}/categories
GET    /users/{user_id}/categories
GET    /categories/{category_id}
PATCH  /categories/{category_id}
DELETE /categories/{category_id}

POST   /users/{user_id}/payment-methods
GET    /users/{user_id}/payment-methods
GET    /payment-methods/{payment_method_id}
PATCH  /payment-methods/{payment_method_id}
DELETE /payment-methods/{payment_method_id}

POST   /users/{user_id}/budgets
GET    /users/{user_id}/budgets
GET    /budgets/{budget_id}
PATCH  /budgets/{budget_id}
DELETE /budgets/{budget_id}
```

Analytics/dashboard endpoints:

```text
GET /users/{user_id}/dashboard
GET /users/{user_id}/dashboard.svg
GET /users/{user_id}/dashboard.html
GET /users/{user_id}/budget-status
```

## Telegram-команды

```text
/start
/help
/add 250 кафе обед
250 кафе обед
/month
/month 05 2026
/dashboard
/dashboard 05 2026
/delete_last
/categories
/add_category кафе
/add_category кафе #ff0000
/payment_methods
/add_payment_method карта
/budget 05 2026 20000
/budget 05 2026 кафе 5000
/budget_status
/budget_status 05 2026
```

## Переменные окружения

Скопируйте пример и заполните токен бота при необходимости:

```bash
cp .env.example .env
```

Основные переменные:

```env
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/postgres
TELEGRAM_BOT_TOKEN=put-your-token-here
TELEGRAM_POLL_TIMEOUT=30
LOG_LEVEL=INFO
```

## Docker

База данных и API:

```bash
docker compose up --build api
```

Только PostgreSQL:

```bash
docker compose up -d db
```

API, база данных и бот:

```bash
TELEGRAM_BOT_TOKEN=your-token docker compose --profile bot up --build
```

## Локальный запуск

Установка зависимостей:

```bash
poetry install
```

Миграции:

```bash
poetry run alembic upgrade head
```

API:

```bash
poetry run uvicorn app.main:app --reload
```

Telegram-бот:

```bash
poetry run python -m app.transport.telegram.bot
```

Тесты:

```bash
poetry run pytest
```

Тесты не обращаются к реальному Telegram API. Они проверяют парсер Telegram-команд, аналитику, API handlers, сервисный слой, создание пользователя, категории, способа оплаты, бюджета, расхода, dashboard, ошибки 404/409/422 и удаление расхода.

Через Docker тесты можно запустить так:

```bash
docker compose run --rm api pytest
```

## Примеры API

Создать пользователя:

```bash
curl -s -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name":"demo","telegram_id":1001}'
```

Создать категорию:

```bash
curl -s -X POST http://localhost:8000/users/$USER_ID/categories \
  -H "Content-Type: application/json" \
  -d '{"name":"кафе","color":"#ff0000"}'
```

Создать общий бюджет:

```bash
curl -s -X POST http://localhost:8000/users/$USER_ID/budgets \
  -H "Content-Type: application/json" \
  -d '{"year":2026,"month":5,"amount":"20000.00"}'
```

Создать расход:

```bash
curl -s -X POST http://localhost:8000/users/$USER_ID/expenses \
  -H "Content-Type: application/json" \
  -d '{"amount":"250.00","category":"кафе","description":"обед"}'
```

Получить dashboard:

```bash
curl -s "http://localhost:8000/users/$USER_ID/dashboard?year=2026&month=5"
curl -s "http://localhost:8000/users/$USER_ID/budget-status?year=2026&month=5"
```

HTML и SVG dashboard открываются в браузере:

```text
http://localhost:8000/users/$USER_ID/dashboard.html?year=2026&month=5
http://localhost:8000/users/$USER_ID/dashboard.svg?year=2026&month=5
```
