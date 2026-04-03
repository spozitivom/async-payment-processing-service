# Async Payment Processing Service

`async-payment-processing-service` — тестовый production-like backend-сервис для асинхронной обработки платежей. Проект показывает, как аккуратно реализовать прием HTTP-запроса, атомарную запись `payment + outbox`, публикацию события в RabbitMQ, фоновую обработку платежа, отправку webhook с retry и отправку финально неуспешных webhook в DLQ.

## Что делает сервис

Сервис принимает запрос на создание платежа, возвращает `202 Accepted`, а дальнейшую обработку выполняет асинхронно:

1. API сохраняет платеж в PostgreSQL со статусом `pending`.
2. В той же транзакции создается outbox-событие `payment.created`.
3. Фоновый dispatcher читает outbox и публикует сообщение в RabbitMQ.
4. Consumer получает сообщение, эмулирует внешний платежный шлюз и переводит платеж в `succeeded` или `failed`.
5. После финализации consumer отправляет webhook клиенту.
6. Если webhook не доставлен, сервис делает retry с экспоненциальной задержкой.
7. После исчерпания retry информация об ошибке доставки уходит в DLQ.

## Бизнес-сценарий

Клиент вызывает `POST /api/v1/payments` с `X-API-Key` и `Idempotency-Key`.

- Если это новый запрос, сервис создает платеж и outbox-событие.
- Если запрос уже приходил с тем же `Idempotency-Key`, новый платеж не создается: сервис возвращает существующую сущность.
- Клиент может опрашивать `GET /api/v1/payments/{payment_id}` и смотреть текущий статус.

## Стек технологий

- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy 2.0 Async
- PostgreSQL
- RabbitMQ
- FastStream
- Alembic
- httpx
- Docker Compose
- pytest
- ruff

## Архитектура

Проект организован по схеме `api -> application -> infrastructure`.

- `api` отвечает только за HTTP-контракты, заголовки, схемы и маппинг ответов.
- `application` содержит use case и сервисы с основной бизнес-логикой.
- `infrastructure` содержит детали БД, брокера, внешних клиентов и Unit of Work.
- `workers` запускают долгоживущие фоновые процессы: dispatcher и consumer.

### Outbox Flow

1. `CreatePaymentUseCase` создает `payments` и `outbox` в одной транзакции.
2. `OutboxDispatcherService` периодически читает `pending`-события.
3. После успешной публикации событие помечается как `published`.
4. Если публикация не удалась, увеличивается `retry_count`, фиксируется ошибка и рассчитывается `next_retry_at`.

### Consumer Flow

1. Consumer получает сообщение `payment.created`.
2. Сервис загружает платеж из БД.
3. Если платеж уже не `pending`, повторная обработка пропускается.
4. Если платеж еще `pending`, запускается эмуляция внешнего шлюза.
5. После обновления статуса отправляется webhook.
6. Если webhook не доставлен после всех retry, событие публикуется в DLQ.

## Структура каталогов

```text
src/
  api/
    routers/
    schemas/
  application/
    dto/
    services/
    use_cases/
  core/
  domain/
  infrastructure/
    broker/
    clients/
    db/
  workers/
tests/
  integration/
  unit/
docker/
migrations/
docs/               # локальная рабочая документация, не коммитится
```

## Переменные окружения

Создай локальный `.env` на основе примера:

```powershell
Copy-Item .env.example .env
```

Или в Unix-shell:

```bash
cp .env.example .env
```

Основные переменные:

- `API_KEY` — статический ключ для доступа к API
- `DATABASE_URL` / `DATABASE_URL_SYNC` — async/sync URL для SQLAlchemy и Alembic
- `RABBITMQ_URL` — адрес RabbitMQ
- `OUTBOX_POLL_INTERVAL` — интервал опроса outbox
- `WEBHOOK_MAX_RETRIES` — количество retry для webhook

## Как поднять проект через Docker Compose

Полный запуск:

```bash
docker compose up --build
```

Что произойдет:

- поднимутся `postgres` и `rabbitmq`
- выполнится сервис `migrate`
- после успешной миграции стартуют `api` и `worker`

Если хочешь запустить сервисы в фоне:

```bash
docker compose up --build -d
```

## Как применить миграции

Отдельный ручной запуск миграций:

```bash
docker compose run --rm migrate
```

## Как запустить API локально без Docker

Нужно, чтобы PostgreSQL и RabbitMQ уже были доступны.

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir src
```

## Как запустить worker локально без Docker

```bash
python -m workers.run_worker
```

Запускать команду нужно из корня репозитория.

## Swagger

Swagger UI:

```text
http://localhost:8000/docs
```

OpenAPI schema:

```text
http://localhost:8000/openapi.json
```

## RabbitMQ Management UI

UI доступен по адресу:

```text
http://localhost:15672
```

Логин и пароль по умолчанию берутся из `.env.example`:

- логин: `guest`
- пароль: `guest`

## Как проверить создание платежа

Пример запроса:

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -H "Idempotency-Key: order-123" \
  -d '{
    "amount": "125.50",
    "currency": "USD",
    "description": "Order #123",
    "metadata": {"order_id": "123"},
    "webhook_url": "http://host.docker.internal:9000/webhook"
  }'
```

Ожидаемое поведение:

- ответ `202 Accepted`
- в теле есть `payment_id`
- в БД создаются записи в `payments` и `outbox`

## Пример POST /api/v1/payments

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -H "Idempotency-Key: order-456" \
  -d '{
    "amount": "99.99",
    "currency": "EUR",
    "description": "Invoice #456",
    "metadata": {"invoice_id": "456"},
    "webhook_url": "http://host.docker.internal:9000/webhook"
  }'
```

## Пример GET /api/v1/payments/{payment_id}

```bash
curl http://localhost:8000/api/v1/payments/<payment_id> \
  -H "X-API-Key: change-me"
```

Пример ответа:

```json
{
  "id": "c38b5e85-f3f3-4a7e-9d1e-6bb39f0dd5b8",
  "amount": "125.50",
  "currency": "USD",
  "description": "Order #123",
  "metadata": {
    "order_id": "123"
  },
  "status": "pending",
  "idempotency_key": "order-123",
  "webhook_url": "http://host.docker.internal:9000/webhook",
  "created_at": "2026-04-03T18:00:00+00:00",
  "processed_at": null,
  "failure_reason": null
}
```

## Как проверить идемпотентность

Повтори тот же `POST /api/v1/payments` с тем же `Idempotency-Key`.

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -H "Idempotency-Key: order-123" \
  -d '{
    "amount": "125.50",
    "currency": "USD",
    "description": "Order #123",
    "metadata": {"order_id": "123"},
    "webhook_url": "http://host.docker.internal:9000/webhook"
  }'
```

Ожидаемое поведение:

- второй ответ тоже успешный
- `payment_id` совпадает с первым запросом
- новая запись в `payments` не создается
- лишние outbox-события не появляются

## Как проверить webhook retry

Самый простой вариант — указать `webhook_url`, который будет возвращать ошибку или недоступен.

Например:

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -H "Idempotency-Key: retry-check-1" \
  -d '{
    "amount": "10.00",
    "currency": "USD",
    "description": "Webhook retry check",
    "metadata": {"case": "retry"},
    "webhook_url": "http://host.docker.internal:9999/webhook"
  }'
```

Дальше смотри логи `worker`: там будут попытки `webhook.retry` с задержками `1s`, `2s`, `4s`.

## Как проверить DLQ

После исчерпания retry webhook-событие должно быть отправлено в DLQ.

Проверка:

1. Отправь платеж с заведомо нерабочим `webhook_url`.
2. Дождись завершения retry.
3. Открой RabbitMQ Management UI.
4. Перейди в очередь `payments.dlq`.
5. Убедись, что там появилось сообщение об ошибке доставки webhook.

## Как смотреть логи контейнеров

Все сервисы:

```bash
docker compose logs -f
```

Только API:

```bash
docker compose logs -f api
```

Только worker:

```bash
docker compose logs -f worker
```

## Как запускать тесты

Все тесты:

```bash
python -m pytest
```

Проверка линтером:

```bash
python -m ruff check .
```

## Сознательные допущения и упрощения

- Один worker-process запускает и polling-dispatcher, и broker consumer.
- Для outbox используется polling, а не CDC.
- Эмуляция платежного шлюза упрощена до случайного успешного/неуспешного результата.
- Retry webhook реализован в application-слое, без отдельного persisted delivery state.

## Ограничения текущего решения

- Нет отдельной таблицы для истории webhook delivery.
- Нет реального distributed lock для нескольких dispatcher-процессов.
- Интеграционные тесты не поднимают реальный RabbitMQ/PostgreSQL в Docker.
- Нет отдельной observability-инфраструктуры: Prometheus, Grafana, OpenTelemetry.
- Нет отдельного webhook delivery service.

## Особенности запуска

- Миграции используют `DATABASE_URL_SYNC`, поэтому для Alembic нужен sync driver.
- Локальный worker следует запускать из корня проекта, потому что импортируется пакет `src`.
- Для webhook на локальной машине внутри Docker удобно использовать `host.docker.internal`.
