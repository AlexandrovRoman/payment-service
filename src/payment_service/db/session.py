"""Async SQLAlchemy engine and session factory.

Follows SQLAlchemy 2.0 patterns:
- create_async_engine with asyncpg dialect
- async_sessionmaker for session creation
- Dependency-injection-friendly get_db() generator for FastAPI
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from payment_service.core.settings import get_settings

settings = get_settings()

engine = create_async_engine(
    str(settings.database_url),
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_pre_ping=True,  # validate connections before use
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,  # avoid lazy-load errors after commit
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session.

    Usage::

        @router.get("/")
        async def handler(db: DbSession) -> ...:
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Convenience type alias for FastAPI dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db)]
