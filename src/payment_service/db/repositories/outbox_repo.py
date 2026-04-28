"""Outbox repository - data access for the Outbox pattern."""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.db.models.outbox import OutboxEvent, OutboxStatus


class OutboxRepository:
    """All database operations related to OutboxEvent entities."""

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
        """Insert a new PENDING outbox event (call inside the same transaction)."""
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

    async def get_pending_events(self, limit: int = 100) -> list[OutboxEvent]:
        """Return up to *limit* unpublished events ordered by creation time."""
        result = await self._session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.status == OutboxStatus.PENDING)
            .order_by(OutboxEvent.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)  # safe for concurrent pollers
        )
        return list(result.scalars().all())

    async def mark_published(self, event: OutboxEvent) -> None:
        """Mark event as successfully published."""
        await self._session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == event.id)
            .values(
                status=OutboxStatus.PUBLISHED,
                published_at=datetime.now(UTC),
                error_message=None,
            )
        )

    async def mark_failed(self, event: OutboxEvent, error: str) -> None:
        """Mark event as permanently failed."""
        await self._session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == event.id)
            .values(
                status=OutboxStatus.FAILED,
                error_message=error[:2000],  # cap at 2000 chars
            )
        )
