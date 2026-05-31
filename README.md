# Telegram expense tracker

Приложение для отслеживания расходов за месяц через Telegram-бота, REST API и аналитический dashboard.

## Возможности

- добавление расходов через Telegram или API;
- хранение пользователей и расходов в PostgreSQL;
- просмотр расходов за выбранный месяц;
- аналитика по сумме, количеству операций, среднему расходу и категориям;
- SVG-график расходов;
- HTML dashboard;
- миграции Alembic;
- тесты для парсинга команд и расчета аналитики.

## Стек

- Python 3.12
- FastAPI
- SQLAlchemy async
- PostgreSQL
- Alembic
- Poetry
- Docker Compose

## Установка

```powershell
poetry install
```

Если зависимости в `pyproject.toml` менялись, обновить lock-файл:

```powershell
poetry lock
poetry install
```

## Переменные окружения

Пример лежит в `.env.example`.

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/postgres
TELEGRAM_BOT_TOKEN=put-your-token-here
TELEGRAM_POLL_TIMEOUT=30
```

Для локального запуска бота в PowerShell:

```powershell
$env:TELEGRAM_BOT_TOKEN="your-token"
```

## Запуск через Docker

API и база данных:

```powershell
docker-compose up --build
```

API будет доступно здесь:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

API, база данных и Telegram-бот:

```powershell
$env:TELEGRAM_BOT_TOKEN="your-token"
docker-compose --profile bot up --build
```

## Локальный запуск

Нужна доступная PostgreSQL база и корректный `DATABASE_URL`.

Миграции:

```powershell
poetry run alembic upgrade head
```

API:

```powershell
poetry run uvicorn app.main:app --reload
```

Telegram-бот:

```powershell
poetry run python -m app.transport.telegram.bot
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
```

Формат добавления расхода:

```text
сумма категория описание
```

Описание необязательное.

## API

Создать пользователя:

```http
POST /users
```

Добавить расход:

```http
POST /users/{user_id}/expenses
```

Получить расходы за месяц:

```http
GET /users/{user_id}/expenses?year=2026&month=5
```

Получить JSON-аналитику:

```http
GET /users/{user_id}/dashboard?year=2026&month=5
```

Открыть HTML dashboard:

```http
GET /users/{user_id}/dashboard.html?year=2026&month=5
```

Открыть SVG-график:

```http
GET /users/{user_id}/dashboard.svg?year=2026&month=5
```

## Как быстро посмотреть dashboard

После запуска `docker-compose up --build` выполни:

```powershell
$user = Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/users `
  -ContentType "application/json" `
  -Body '{"name":"demo"}'

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/users/$($user.id)/expenses" `
  -ContentType "application/json" `
  -Body '{"amount":250,"category":"cafe","description":"lunch"}'

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/users/$($user.id)/expenses" `
  -ContentType "application/json" `
  -Body '{"amount":1200,"category":"products","description":"dinner"}'

"http://localhost:8000/users/$($user.id)/dashboard.html"
"http://localhost:8000/users/$($user.id)/dashboard.svg"
```

Последние две ссылки открой в браузере.

## Тесты

```powershell
poetry run python -m pytest
```

Дополнительная проверка импорта и синтаксиса:

```powershell
poetry run python -m compileall app tests
```

## Структура проекта

```text
app/
  core/                 настройки и логирование
  domain/               доменные сущности
  repositories/         модели БД и репозитории
  transport/api/        REST API
  transport/telegram/   Telegram-бот
  usecase/              бизнес-логика и аналитика
migrations/             Alembic-миграции
tests/                  тесты
```
