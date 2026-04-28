"""Authentication dependencies."""

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from payment_service.core.settings import get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


async def verify_api_key(api_key: str = Security(_api_key_header)) -> None:
    """FastAPI dependency: verify the static X-API-Key header.

    Raises HTTP 403 if the key is missing or incorrect.
    """
    settings = get_settings()
    if api_key != settings.api_key.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key",
        )
