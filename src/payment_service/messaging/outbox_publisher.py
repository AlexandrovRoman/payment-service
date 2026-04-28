"""Outbox publisher.

Runs as a background task alongside the FastAPI app.
Polls the outbox_events table for PENDING events and publishes them
to RabbitMQ via the FastStream broker.
"""

import asyncio
import json
import logging

from faststream.rabbit import RabbitBroker

from payment_service.core.settings import get_settings
from payment_service.db.models.outbox import OutboxEvent
from payment_service.db.repositories import OutboxRepository
from payment_service.db.session import AsyncSessionLocal
from payment_service.messaging.broker import payments_exchange

logger = logging.getLogger(__name__)
settings = get_settings()


async def _publish_event(broker: RabbitBroker, event: OutboxEvent) -> None:
    """Publish a single outbox event to RabbitMQ."""
    await broker.publish(
        message=json.dumps(event.payload),
        exchange=payments_exchange,
        routing_key=event.routing_key,
        content_type="application/json",
        message_id=event.id,
        headers={"aggregate_type": event.aggregate_type},
    )


async def run_outbox_publisher(broker: RabbitBroker) -> None:
    """Continuously poll for pending outbox events and publish them.

    Runs in an infinite loop; designed to be started as an asyncio task.
    """
    logger.info("Outbox publisher started")
    while True:
        try:
            async with AsyncSessionLocal() as session:
                repo = OutboxRepository(session)
                events = await repo.get_pending_events(limit=100)

                for event in events:
                    try:
                        await _publish_event(broker, event)
                        await repo.mark_published(event)
                        logger.debug(
                            "Outbox event published",
                            extra={"event_id": event.id, "type": event.event_type},
                        )
                    except Exception as exc:
                        logger.error(
                            "Failed to publish outbox event",
                            extra={"event_id": event.id, "error": str(exc)},
                        )
                        await repo.mark_failed(event, str(exc))

                await session.commit()

        except Exception as exc:
            logger.error(f"Outbox publisher cycle error: {exc}")

        await asyncio.sleep(settings.outbox_poll_interval)
