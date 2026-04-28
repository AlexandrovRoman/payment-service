"""Webhook sender with exponential-backoff retries."""

import asyncio
import logging

import httpx

from payment_service.api.v1.schemas import WebhookPayload
from payment_service.core.exceptions import WebhookDeliveryError
from payment_service.core.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_BASE_BACKOFF = 1.0  # seconds
_BACKOFF_FACTOR = 2.0


async def send_webhook(payload: WebhookPayload, url: str) -> None:
    """Deliver a webhook notification with exponential backoff retries.

    Attempts up to ``settings.webhook_max_retries`` times before giving up.

    Args:
        payload:  The webhook payload to send.
        url:      The client-supplied callback URL.

    Raises:
        WebhookDeliveryError: if all retry attempts are exhausted.
    """
    data = payload.model_dump_json()
    for attempt in range(1, settings.webhook_max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=settings.webhook_timeout) as client:
                response = await client.post(
                    url,
                    content=data,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                logger.info(
                    "Webhook delivered",
                    extra={
                        "payment_id": payload.payment_id,
                        "url": url,
                        "attempt": attempt,
                        "status_code": response.status_code,
                    },
                )
                return
        except Exception as exc:
            backoff = _BASE_BACKOFF * (_BACKOFF_FACTOR ** (attempt - 1))
            logger.warning(
                "Webhook delivery failed, retrying",
                extra={
                    "payment_id": payload.payment_id,
                    "url": url,
                    "attempt": attempt,
                    "error": str(exc),
                    "backoff": backoff,
                },
            )
            if attempt < settings.webhook_max_retries:
                await asyncio.sleep(backoff)

    raise WebhookDeliveryError(url=url, attempts=settings.webhook_max_retries)
