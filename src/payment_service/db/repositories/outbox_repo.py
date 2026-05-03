from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.db.models.outbox import OutboxEvent, OutboxStatus


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_event(
        self,
        *,
        event_id: str,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict,
        routing_key: str,
    ) -> OutboxEvent:
        event = OutboxEvent(
            id=event_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
            routing_key=routing_key,
            status=OutboxStatus.PENDING,
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def get_payment_event(self, *, payment_id: str) -> OutboxEvent | None:
        result = await self._session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == payment_id,
                OutboxEvent.aggregate_type == "payment",
            )
        )
        return result.scalar_one_or_none()

    async def get_pending_events(self, limit: int = 100) -> list[OutboxEvent]:
        result = await self._session.execute(
            select(OutboxEvent)
            .where(
                OutboxEvent.status == OutboxStatus.PENDING,
            )
            .order_by(OutboxEvent.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result.scalars().all())

    async def mark_published(self, event: OutboxEvent) -> None:
        await self._session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == event.id)
            .values(
                status=OutboxStatus.PUBLISHED,
                published_at=datetime.now(UTC),
                error_message=None,
            )
        )
