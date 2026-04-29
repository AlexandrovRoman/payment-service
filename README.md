# payment-service

Async payment processing microservice built with **FastAPI**, **SQLAlchemy 2.0**, **RabbitMQ (FastStream)**, and the **Outbox pattern** for guaranteed event delivery.

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.115+ |
| Validation | Pydantic v2 |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 |
| Migrations | Alembic |
| Messaging | RabbitMQ + FastStream |
| Package mgr | **uv** |
| Linter/fmt | Ruff |
| Type checker | mypy (strict) |
| Tests | pytest + pytest-asyncio |
| Containers | Docker + Compose |

## Quick Start

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (for local dev)

### 1. Start with Docker Compose

```bash
cd payment-service
cp .env.example .env

make docker-build
make docker-logs
```

The API is now available at **http://localhost:8000**.

### 2. Local development

```bash
# Install dependencies
make install-dev

# Copy and configure environment
cp .env.example .env
# Edit .env with your values

# Start only infrastructure
docker compose up -d postgres rabbitmq

# Apply migrations
make migrate

# Run API (with hot reload)
make dev-api

# In another terminal: run consumer worker
make dev-worker
```

## API Usage

### Authentication

All endpoints require `X-API-Key` header:

```http
X-API-Key: your-api-key
```

### Create a Payment

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: super-secret-key" \
  -H "Idempotency-Key: unique-key-12345" \
  -d '{
    "amount": "1500.00",
    "currency": "RUB",
    "description": "Order #42",
    "metadata": {"order_id": 42, "user_id": 7},
    "webhook_url": "https://your-service.com/webhooks/payment"
  }'
```

**Response** `202 Accepted`:
```json
{
  "payment_id": "01JKABCDEF...",
  "status": "pending",
  "created_at": "2025-01-15T10:30:00Z"
}
```

### Get Payment Details

```bash
curl http://localhost:8000/api/v1/payments/01JKABCDEF... \
  -H "X-API-Key: super-secret-key"
```

**Response** `200 OK`:
```json
{
  "payment_id": "01JKABCDEF...",
  "idempotency_key": "unique-key-12345",
  "amount": "1500.00",
  "currency": "RUB",
  "description": "Order #42",
  "metadata": {"order_id": 42, "user_id": 7},
  "webhook_url": "https://your-service.com/webhooks/payment",
  "status": "succeeded",
  "created_at": "2025-01-15T10:30:00Z",
  "processed_at": "2025-01-15T10:30:04Z"
}
```

### Webhook Payload

When processing completes, we POST to your `webhook_url`:

```json
{
  "payment_id": "01JKABCDEF...",
  "status": "succeeded",
  "amount": "1500.00",
  "currency": "RUB",
  "processed_at": "2025-01-15T10:30:04Z"
}
```

## Interactive API Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- RabbitMQ Management: http://localhost:15672 (payment / payment)

## Running Tests

```bash
docker compose up -d postgres

# All unit tests
make test-unit

# With coverage report
make test-cov

# Open coverage report
open htmlcov/index.html
```

## Useful Make Commands

```bash
make help          # list all commands
make lint          # ruff linter
make format        # ruff formatter + auto-fix
make typecheck     # mypy strict
make migrate       # apply all migrations
make migrate-create name="add_index"  # create migration
make docker-logs-api    # follow API logs
make docker-logs-worker # follow consumer logs
make docker-down-v      # stop + remove volumes
```
