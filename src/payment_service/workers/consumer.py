"""Payment consumer worker.

A single FastStream consumer that:
1. Receives a ``payment.created`` event from ``payments.new`` queue.
2. Calls the (emulated) payment gateway.
3. Updates the payment status in the database.
4. Sends a webhook notification to the client.
5. Implements retry logic with exponential back-off (max 3 attempts).
6. After 3 failed attempts, RabbitMQ nacks the message → DLQ.
"""

import asyncio
import json
import logging

from faststream import FastStream
from faststream.rabbit import RabbitMessage

from payment_service.api.v1.schemas import PaymentCreatedEvent, WebhookPayload
from payment_service.core.logging import configure_logging
from payment_service.core.settings import get_settings
from payment_service.db.models.payment import PaymentStatus
from payment_service.db.repositories import PaymentRepository
from payment_service.db.session import AsyncSessionLocal
from payment_service.messaging.broker import (
    broker,
    payments_exchange,
    payments_new_queue,
)
from payment_service.services.gateway import process_payment
from payment_service.services.webhook import send_webhook

logger = logging.getLogger(__name__)
settings = get_settings()

_MAX_ATTEMPTS = settings.max_retry_attempts
_BASE_BACKOFF = 1.0  # seconds


# ── FastStream application ────────────────────────────────────────────────────
app = FastStream(broker)


@broker.subscriber(
    queue=payments_new_queue,
    exchange=payments_exchange,
    retry=False,  # we handle retries manually
)
async def handle_payment_created(msg: RabbitMessage) -> None:
    """Process a single payment event end-to-end.

    Manual retry loop:
    - On success: ack the message.
    - On transient error: wait with exponential backoff and retry.
    - After *_MAX_ATTEMPTS* failures: nack without requeue → message
      goes to the Dead Letter Exchange (DLX) → DLQ.
    """
    raw = await msg.body()
    event = PaymentCreatedEvent.model_validate(json.loads(raw))
    payment_id = event.payment_id

    logger.info("Received payment event", extra={"payment_id": payment_id})

    last_exc: Exception | None = None

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            await _process(event)
            await msg.ack()
            logger.info(
                "Payment processed successfully",
                extra={"payment_id": payment_id, "attempt": attempt},
            )
            return
        except Exception as exc:
            last_exc = exc
            backoff = _BASE_BACKOFF * (2 ** (attempt - 1))
            logger.warning(
                "Processing attempt failed",
                extra={
                    "payment_id": payment_id,
                    "attempt": attempt,
                    "max_attempts": _MAX_ATTEMPTS,
                    "error": str(exc),
                    "backoff_seconds": backoff,
                },
            )
            if attempt < _MAX_ATTEMPTS:
                await asyncio.sleep(backoff)

    # All retries exhausted → send to DLQ
    logger.error(
        "Payment permanently failed, routing to DLQ",
        extra={"payment_id": payment_id, "error": str(last_exc)},
    )
    await msg.nack(requeue=False)


async def _process(event: PaymentCreatedEvent) -> None:
    """Core processing logic: gateway → DB update → webhook."""
    # 1. Call payment gateway (emulated)
    result = await process_payment(
        payment_id=event.payment_id,
        amount=event.amount,
        currency=event.currency,
    )

    new_status = PaymentStatus.SUCCEEDED if result.success else PaymentStatus.FAILED

    # 2. Update payment status in DB
    async with AsyncSessionLocal() as session:
        repo = PaymentRepository(session)
        payment = await repo.get_by_id(event.payment_id)
        if payment is None:
            raise ValueError(f"Payment {event.payment_id!r} not found in DB")

        updated = await repo.update_status(payment, new_status)
        await session.commit()

    # 3. Send webhook (if configured)
    if event.webhook_url:
        payload = WebhookPayload(
            payment_id=event.payment_id,
            status=new_status,
            amount=updated.amount,
            currency=updated.currency,
            processed_at=updated.processed_at,
        )
        await send_webhook(payload, event.webhook_url)


def run() -> None:
    """Entry point for the consumer worker process."""
    configure_logging(debug=settings.debug)
    asyncio.run(app.run())


if __name__ == "__main__":
    run()
