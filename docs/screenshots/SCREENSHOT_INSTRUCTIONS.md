# Инструкции по скриншотам для отчета

Папка для скриншотов: `docs/screenshots/`.

API и база были проверены через Docker. Для ручного повторения:

```bash
docker compose up -d api
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## Уже подготовленные автоматические скриншоты

| Файл | Что изображено | Как получен |
|---|---|---|
| `01_swagger_endpoints.png` | Swagger UI со списком endpoints | headless Chrome |
| `06_expenses_list.png` | JSON-ответ со списком расходов | headless Chrome |
| `07_dashboard_json.png` | JSON dashboard | headless Chrome |
| `08_dashboard_html.png` | HTML dashboard | headless Chrome |
| `09_dashboard_svg.png` | SVG-график dashboard | headless Chrome |
| `10_budget_status.png` | JSON budget status | headless Chrome |

Демо-пользователь для этих скриншотов был создан в Docker PostgreSQL:

```text
user_id=2bd63c81-9c69-46dd-8e27-37773a249087
category_id=0e37e273-2b8d-45b1-9cea-095a0a4523eb
payment_method_id=8b8c5074-0f33-4c40-968c-044680c2db0c
```

Демо-ссылки:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/users/2bd63c81-9c69-46dd-8e27-37773a249087/expenses?year=2026&month=5
http://127.0.0.1:8000/users/2bd63c81-9c69-46dd-8e27-37773a249087/dashboard?year=2026&month=5
http://127.0.0.1:8000/users/2bd63c81-9c69-46dd-8e27-37773a249087/dashboard.html?year=2026&month=5
http://127.0.0.1:8000/users/2bd63c81-9c69-46dd-8e27-37773a249087/dashboard.svg?year=2026&month=5
http://127.0.0.1:8000/users/2bd63c81-9c69-46dd-8e27-37773a249087/budget-status?year=2026&month=5
```

## Скриншоты, которые нужно сделать вручную

### `02_create_user.png`

Открыть Swagger `POST /users`, нажать **Try it out**, отправить:

```json
{"name":"demo-report","telegram_id":1001}
```

Сделать скриншот ответа `201`.

### `03_create_category.png`

Открыть `POST /users/{user_id}/categories`, вставить id пользователя из предыдущего шага, отправить:

```json
{"name":"кафе","color":"#ff0000"}
```

Сделать скриншот ответа `201`.

### `04_create_budget.png`

Открыть `POST /users/{user_id}/budgets`, отправить:

```json
{"year":2026,"month":5,"amount":"20000.00"}
```

Сделать скриншот ответа `201`.

### `05_create_expense.png`

Открыть `POST /users/{user_id}/expenses`, отправить:

```json
{
  "amount":"250.00",
  "category":"кафе",
  "description":"обед",
  "spent_at":"2026-05-10T12:00:00+00:00"
}
```

Сделать скриншот ответа `201`.

### `11_tests_passed.png`

В терминале выполнить:

```bash
docker compose run --rm api pytest -v
```

Сделать скриншот финального результата `21 passed`.

### `12_docker_running.png`

В терминале выполнить:

```bash
docker compose ps
```

Сделать скриншот, где сервисы `db` и `api` находятся в состоянии `healthy`.

### `13_alembic_migrations.png`

В терминале выполнить:

```bash
docker compose exec -T api alembic current
```

Сделать скриншот с revision `20260601_0002 (head)`.

### Telegram-скриншоты `14`-`18`

Нужен реальный `TELEGRAM_BOT_TOKEN`.

Запуск:

```bash
TELEGRAM_BOT_TOKEN=your-token docker compose --profile bot up --build
```

В Telegram отправить команды и сделать скриншоты:

| Файл | Команда | Что должно быть видно |
|---|---|---|
| `14_bot_start_help.png` | `/start` или `/help` | список команд |
| `15_bot_add_expense.png` | `/add 250 кафе обед` | сообщение о добавленном расходе |
| `16_bot_month.png` | `/month 05 2026` | итоги месяца |
| `17_bot_dashboard.png` | `/dashboard 05 2026` | SVG-документ dashboard |
| `18_bot_budget_status.png` | `/budget_status 05 2026` | лимит, потрачено, остаток, процент |
