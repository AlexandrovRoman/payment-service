import asyncio
import json
import logging

from faststream import FastStream
from faststream.rabbit import RabbitMessage

from payment_service.api.v1.schemas import PaymentCreatedEvent, WebhookPayload
from payment_service.core.logging import configure_logging
from payment_service.core.settings import settings
from payment_service.db.models import OutboxStatus
from payment_service.db.models.payment import PaymentStatus
from payment_service.db.repositories import OutboxRepository, PaymentRepository
from payment_service.db.session import AsyncSessionLocal
from payment_service.services.gateway import process_payment
from payment_service.services.webhook import send_webhook
from payment_service.workers.broker import (
    broker,
    payments_dlq_queue,
    payments_exchange,
    payments_new_queue,
)
from payment_service.workers.outbox_publisher import _publish_to_dlq, run_outbox_publisher

logger = logging.getLogger(__name__)

app = FastStream(broker)


@broker.subscriber(
    queue=payments_new_queue,
    exchange=payments_exchange,
)
async def handle_payment_created(msg: RabbitMessage) -> None:
    raw = msg.body
    event = PaymentCreatedEvent.model_validate(json.loads(raw))
    payment_id = event.payment_id

    logger.info("Received payment event", extra={"payment_id": payment_id})

    try:
        await _process(event)
        await msg.ack()
        logger.info(
            "Payment processed successfully",
            extra={"payment_id": payment_id},
        )
    except Exception as exc:
        await _process_error(event, exc)
        logger.error(
            "Payment failed",
            extra={"payment_id": payment_id, "error": str(exc)},
        )
        await msg.nack(requeue=False)


async def _process(event: PaymentCreatedEvent) -> None:
    result = await process_payment(
        payment_id=event.payment_id,
        amount=event.amount,
        currency=event.currency,
    )

    new_status = PaymentStatus.SUCCEEDED if result.success else PaymentStatus.FAILED

    async with AsyncSessionLocal() as session:
        payment_repo = PaymentRepository(session)
        payment = await payment_repo.get_by_id(event.payment_id)
        if payment is None:
            raise ValueError(f"Payment {event.payment_id!r} not found in DB")
        updated = await payment_repo.update_status(payment, new_status)
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


async def _process_error(event: PaymentCreatedEvent, exc: Exception) -> None:
    async with AsyncSessionLocal() as session:
        outbox_repo = OutboxRepository(session)
        db_event = await outbox_repo.get_payment_event(payment_id=event.payment_id)
        if not db_event:
            logger.error(
                "Event not found in DB",
                extra={"payment_id": event.payment_id, "aggregate_type": "payment"},
            )
            return
        await outbox_repo.mark_to_resend(db_event, str(exc))
        if db_event.status == OutboxStatus.FAILED:
            logger.info("Route event to dlq")
            await _publish_to_dlq(broker, db_event)
        payment_repo = PaymentRepository(session)
        payment = await payment_repo.get_by_id(event.payment_id)
        if payment is None:
            logger.error("Payment not found in DB", extra={"payment_id": event.payment_id})
        else:
            await payment_repo.update_status(payment, PaymentStatus.FAILED)
        await session.commit()


@app.after_startup
async def bind_queue_exchange() -> None:
    await broker.declare_exchange(payments_exchange)
    await broker.declare_queue(payments_new_queue)
    pika_payments_dlq_queue = await broker.declare_queue(payments_dlq_queue)

    await pika_payments_dlq_queue.bind(
        payments_exchange.name, routing_key=payments_dlq_queue.routing_key
    )


async def run() -> None:
    """Entry point for the publisher and consumer worker process."""
    configure_logging(debug=settings.debug)
    await broker.connect()
    await asyncio.gather(run_outbox_publisher(broker), app.run())


if __name__ == "__main__":
    asyncio.run(run())
