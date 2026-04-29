import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from payment_service.api.v1.deps import verify_api_key
from payment_service.api.v1.payments import router as payments_router
from payment_service.core.settings import settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Async payment processing microservice",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(
        payments_router,
        dependencies=[Depends(verify_api_key)],
    )

    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run(
        "payment_service.main:app",
        host="0.0.0.0",  # noqa: S104
        port=8000,
        reload=settings.debug,
    )
