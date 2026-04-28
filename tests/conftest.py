"""Shared pytest fixtures.

Uses in-memory SQLite for unit tests (fast, no Docker needed).
"""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Must set env vars BEFORE importing any payment_service module
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost/test"
os.environ["RABBITMQ_URL"] = "amqp://guest:guest@localhost/"
os.environ["API_KEY"] = "test-key"

from payment_service.db.base import Base
from payment_service.db.session import get_db
from payment_service.main import create_app

# ── SQLite in-memory engine for unit tests ────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def create_tables() -> AsyncGenerator[None, None]:
    """Create all tables before each test and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with overridden DB dependency and API key."""
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "test-key"},
    ) as ac:
        yield ac


# ── Common test data ───────────────────────────────────────────────────────────


@pytest.fixture
def payment_payload() -> dict:
    return {
        "amount": "100.00",
        "currency": "RUB",
        "description": "Test payment",
        "webhook_url": "https://example.com/webhook",
    }
