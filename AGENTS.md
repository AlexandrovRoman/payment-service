# AGENTS.md – AI Coding Assistant Guide

This file follows the [agents.md open standard](https://agents.md/) and provides
project-specific guidance for AI coding assistants (Cursor, Aider, GitHub Copilot, etc.).

## Project Overview

**payment-service** is an async payment processing microservice built with:
- **FastAPI** (HTTP API)
- **SQLAlchemy 2.0 async** (ORM, async sessions)
- **FastStream + RabbitMQ** (message broker)
- **Outbox pattern** (guaranteed event delivery)
- **uv** (package management)

## Python Standards

- Python **3.12+** required
- All code uses **async/await** – never blocking I/O
- **Type hints everywhere** – mypy strict mode is enforced
- Use `from __future__ import annotations` only when needed for forward refs
- Prefer `X | None` over `Optional[X]`
- Use `str | None` not `Optional[str]`

## Package Management

```bash
# Install all dependencies (including dev)
uv sync

# Add a production dependency
uv add <package>

# Add a dev dependency
uv add --dev <package>

# Run any command in the project venv
uv run <command>
```

Never use `pip install` directly.

## Code Style

- **Formatter/linter**: Ruff (replaces black + flake8 + isort)
- **Line length**: 100 characters
- **Quotes**: double quotes
- Run `make format` before committing

## Architecture

```
src/payment_service/
├── main.py              # FastAPI app factory + lifespan
├── core/
│   ├── settings.py      # Pydantic Settings (single source of truth)
│   ├── exceptions.py    # Domain exceptions
│   └── logging.py       # Logging configuration
├── db/
│   ├── base.py          # SQLAlchemy DeclarativeBase
│   ├── session.py       # Engine, session factory, get_db() dep
│   ├── models/          # ORM models (Payment, OutboxEvent)
│   └── repositories/    # Data access layer
├── api/v1/
│   ├── payments.py      # Route handlers
│   ├── schemas.py       # Pydantic request/response models
│   └── deps.py          # FastAPI dependencies (auth)
├── messaging/
│   ├── broker.py        # FastStream broker + topology
│   └── outbox_publisher.py  # Background outbox poller
├── services/
│   ├── payment_service.py  # Business logic
│   ├── gateway.py          # External gateway emulator
│   └── webhook.py          # Webhook delivery with retries
└── workers/
    └── consumer.py      # RabbitMQ consumer (separate process)
```

## Key Patterns

### Database sessions
Always use the `get_db()` dependency in FastAPI routes.
For background tasks, use `AsyncSessionLocal()` as an async context manager.

### Outbox pattern
When creating a payment:
1. Insert `Payment` record
2. Insert `OutboxEvent` record in the **same transaction**
3. The background `Outbox Publisher` polls and publishes to RabbitMQ

Never publish directly to RabbitMQ from the API handler.

### Repository pattern
All DB access goes through repository classes in `db/repositories/`.
Never write raw SQLAlchemy queries in routes or services.

### Consumer retries
The consumer handles retries manually with exponential backoff.
After `max_retry_attempts` failures, message is nack'd → goes to DLQ.

## Testing

```bash
make test          # all tests
make test-unit     # fast unit tests only (no docker needed)
make test-cov      # with HTML coverage report
```

Unit tests use SQLite in-memory; no external services needed.

## Running Locally

```bash
# Start infrastructure
make docker-up

# Apply migrations
make migrate

# Run API (hot reload)
make dev-api

# Run consumer worker
make dev-worker
```

## Conventions

- IDs use **ULID** (time-sortable, URL-safe)
- Decimal amounts stored as `NUMERIC(18,2)` – never floats
- All timestamps are **timezone-aware UTC**
- Pydantic models use `model_config = ConfigDict(from_attributes=True)` for ORM mapping
- Settings are loaded once via `get_settings()` (lru_cache singleton)
