import asyncio
import json
import logging

from faststream import FastStream
from faststream.rabbit import RabbitMessage

from payment_service.api.v1.schemas import PaymentCreatedEvent, WebhookPayload
from payment_service.core.exceptions import ExternalPaymentServiceError
from payment_service.core.logging import configure_logging
from payment_service.core.settings import settings
from payment_service.db.models.payment import PaymentStatus
from payment_service.db.repositories import PaymentRepository
from payment_service.db.session import AsyncSessionLocal
from payment_service.services.gateway import process_payment
from payment_service.services.webhook import send_webhook
from payment_service.workers.broker import (
    broker,
    payments_dlq,
    payments_dlx,
    payments_exchange,
    payments_new_queue,
)
from payment_service.workers.outbox_publisher import run_outbox_publisher

logger = logging.getLogger(__name__)

app = FastStream(broker)


@broker.subscriber(
    queue=payments_new_queue,
    exchange=payments_exchange,
)
async def handle_payment_created(msg: RabbitMessage) -> None:
    event = PaymentCreatedEvent.model_validate(json.loads(msg.body))
    payment_id = event.payment_id

    logger.info("Received payment event", extra={"payment_id": payment_id})

    try:
        already_processed = await _process(event)

        if already_processed:
            logger.info(
                "Payment already processed, skipping",
                extra={"payment_id": payment_id},
            )

        await msg.ack()

    except ExternalPaymentServiceError as exc:
        logger.warning(
            "Gateway error, will retry",
            extra={"payment_id": payment_id, "error": str(exc)},
        )
        await msg.nack(requeue=True)

    except Exception as exc:
        logger.error(
            "Unrecoverable error, sending to DLQ",
            extra={"payment_id": payment_id, "error": str(exc)},
        )
        await msg.nack(requeue=False)


async def _process(event: PaymentCreatedEvent) -> bool:
    """Process payment event. Return True if payment was processed."""
    async with AsyncSessionLocal() as session:
        payment_repo = PaymentRepository(session)
        payment = await payment_repo.take_to_processing(event.payment_id)
        if not payment:
            return True
        await session.commit()

    try:
        result = await process_payment(
            payment_id=event.payment_id,
            amount=event.amount,
            currency=event.currency,
        )
    except Exception:
        async with AsyncSessionLocal() as session:
            payment_repo = PaymentRepository(session)
            await payment_repo.rollback_to_pending(event.payment_id)
            await session.commit()
        raise

    new_status = PaymentStatus.SUCCEEDED if result.success else PaymentStatus.FAILED

    async with AsyncSessionLocal() as session:
        payment_repo = PaymentRepository(session)

        updated = await payment_repo.update_status_if_pending(event.payment_id, new_status)
        await session.commit()

    if event.webhook_url:
        payload = WebhookPayload(
            payment_id=event.payment_id,
            status=new_status,
            amount=updated.amount,
            currency=updated.currency,
            processed_at=updated.processed_at,
        )
        await send_webhook(payload, event.webhook_url)

    return False


@app.after_startup
async def declare_topology() -> None:
    await broker.declare_exchange(payments_exchange)
    await broker.declare_exchange(payments_dlx)
    declared_dlq = await broker.declare_queue(payments_dlq)
    await declared_dlq.bind(payments_dlx.name)
    await broker.declare_queue(payments_new_queue)


async def run() -> None:
    configure_logging(debug=settings.debug)
    await broker.connect()
    await asyncio.gather(run_outbox_publisher(broker), app.run())


if __name__ == "__main__":
    asyncio.run(run())
