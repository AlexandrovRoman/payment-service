import asyncio
import logging

import httpx

from payment_service.api.v1.schemas import WebhookPayload
from payment_service.core.exceptions import WebhookDeliveryError
from payment_service.core.settings import settings

logger = logging.getLogger(__name__)


async def send_webhook(payload: WebhookPayload, url: str) -> None:
    data = payload.model_dump_json()
    for attempt in range(1, settings.webhook_max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=settings.webhook_timeout_sec) as client:
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
            backoff = settings.webhook_base_backoff_sec * (
                settings.webhook_backoff_factor ** (attempt - 1)
            )
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
