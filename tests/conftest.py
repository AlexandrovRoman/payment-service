from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from payment_service.db.base import Base
from payment_service.db.models import Currency, OutboxStatus, PaymentStatus
from payment_service.db.session import get_db
from payment_service.main import create_app, settings

_TEST_DB_URL = str(settings.database_url)


@pytest_asyncio.fixture(scope="function")
async def pg_schema() -> AsyncGenerator[str, None]:
    schema = "test_main"

    admin = create_async_engine(_TEST_DB_URL, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        await conn.execute(text(f'SET search_path TO "{schema}", public'))
    await admin.dispose()

    yield schema


@pytest_asyncio.fixture(scope="function")
async def test_engine(pg_schema: str) -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(
        _TEST_DB_URL,
        pool_size=5,
        max_overflow=0,
        pool_timeout=10,
        echo=False,
    )

    engine = engine.execution_options(schema_translate_map={None: pg_schema})

    async with engine.begin() as conn:
        await _create_enum_types(conn, pg_schema)

        for table in Base.metadata.tables.values():
            table.schema = pg_schema

        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


async def _create_enum_types(conn: AsyncConnection, schema: str) -> None:
    enums = [
        ("currency_enum", Currency),
        ("payment_status_enum", PaymentStatus),
        ("outbox_status_enum", OutboxStatus),
    ]

    for type_name, enum_cls in enums:
        values = [e.value for e in enum_cls]
        await conn.execute(
            text(f"""
            DO $$
            BEGIN
                CREATE TYPE "{schema}".{type_name} AS ENUM ({", ".join(f"'{v}'" for v in values)});
            EXCEPTION WHEN duplicate_object THEN
                NULL;
            END $$;
        """)
        )


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        autoflush=False,
    )
    async with factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "test-key"},
    ) as ac:
        yield ac


@pytest.fixture
def payment_payload() -> dict[str, object]:
    return {
        "amount": "100.00",
        "currency": "RUB",
        "description": "Test payment",
        "webhook_url": "https://example.com/webhook",
    }
