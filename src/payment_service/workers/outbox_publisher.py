import asyncio
import json
import logging

from faststream.rabbit import RabbitBroker

from payment_service.core.settings import settings
from payment_service.db.models.outbox import OutboxEvent
from payment_service.db.repositories import OutboxRepository
from payment_service.db.session import AsyncSessionLocal
from payment_service.workers.broker import payments_exchange

logger = logging.getLogger(__name__)


async def _publish_event(broker: RabbitBroker, event: OutboxEvent) -> None:
    await broker.publish(
        message=json.dumps(event.payload),
        exchange=payments_exchange,
        routing_key=event.routing_key,
        content_type="application/json",
        message_id=event.id,
        headers={"aggregate_type": event.aggregate_type},
    )


async def run_outbox_publisher(broker: RabbitBroker) -> None:
    logger.info("Outbox publisher started")

    while True:
        try:
            async with AsyncSessionLocal() as session:
                outbox_repo = OutboxRepository(session)

                events = await outbox_repo.get_pending_events(limit=settings.publish_batch_size)

                if not events:
                    await asyncio.sleep(settings.outbox_poll_interval_sec)
                    continue

                for event in events:
                    try:
                        await _publish_event(broker, event)
                    except Exception as exc:
                        logger.exception(
                            "Publish outbox event failed",
                            extra={
                                "error": str(exc),
                                "event_id": event.id,
                                "type": event.event_type,
                            },
                        )
                    else:
                        await outbox_repo.mark_published(event)
                        logger.debug(
                            "Outbox event published",
                            extra={
                                "event_id": event.id,
                                "type": event.event_type,
                            },
                        )

                await session.commit()

        except Exception as exc:
            logger.exception("Outbox publisher cycle failed", extra={"error": str(exc)})

        await asyncio.sleep(settings.outbox_poll_interval_sec)
