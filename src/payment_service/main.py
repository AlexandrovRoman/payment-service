"""FastAPI application factory.

Uses the lifespan context manager (FastAPI 0.95+) to manage startup/shutdown:
  - Connect to RabbitMQ broker
  - Start the Outbox publisher background task
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from payment_service.api.v1.deps import verify_api_key
from payment_service.api.v1.payments import router as payments_router
from payment_service.core.logging import configure_logging
from payment_service.core.settings import get_settings
from payment_service.messaging.broker import broker
from payment_service.messaging.outbox_publisher import run_outbox_publisher

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle resources."""
    configure_logging(debug=settings.debug)
    logger.info("Starting %s", settings.app_name)

    # Connect to RabbitMQ
    await broker.connect()
    logger.info("Connected to RabbitMQ")

    # Start outbox publisher as a background task
    outbox_task = asyncio.create_task(run_outbox_publisher(broker))
    logger.info("Outbox publisher started")

    yield  # ← application runs here

    # Shutdown
    outbox_task.cancel()
    try:
        await outbox_task
    except asyncio.CancelledError:
        pass

    await broker.close()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""
    app = FastAPI(
        title="Payment Service",
        description="Async payment processing microservice",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS - tighten in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # All routes require a valid X-API-Key
    app.include_router(
        payments_router,
        dependencies=[Depends(verify_api_key)],
    )

    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


# Module-level app used by uvicorn
app = create_app()


def run() -> None:
    """Convenience entry point for `uv run payment-service`."""
    import uvicorn

    uvicorn.run(
        "payment_service.main:app",
        host="0.0.0.0",  # noqa: S104
        port=8000,
        reload=settings.debug,
    )
