"""Outbox ORM model.

The Outbox pattern guarantees that domain events are published to the
message broker **if and only if** the database transaction commits.

Flow:
  1. Payment + OutboxEvent are written in the **same transaction**.
  2. A background poller queries unpublished events.
  3. The poller publishes each event to RabbitMQ and marks it published.

This avoids the dual-write problem: if the broker is down, events are
safely stored in the DB and will be published once the broker recovers.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Enum, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from payment_service.db.base import Base


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"


class OutboxEvent(Base):
    """Single event stored in the outbox table."""

    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    """ULID identifier for the event."""

    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    """Type of the domain object that raised the event, e.g. 'payment'."""

    aggregate_id: Mapped[str] = mapped_column(String(26), nullable=False)
    """ID of the domain object (payment_id)."""

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    """Event name, e.g. 'payment.created'."""

    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    """JSON payload to publish."""

    routing_key: Mapped[str] = mapped_column(String(255), nullable=False)
    """RabbitMQ routing key for the event."""

    status: Mapped[OutboxStatus] = mapped_column(
        Enum(OutboxStatus, name="outbox_status_enum"),
        nullable=False,
        default=OutboxStatus.PENDING,
        server_default=OutboxStatus.PENDING.value,
    )

    error_message: Mapped[str | None] = mapped_column(Text)
    """Last error message when publication failed."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        # Index to efficiently find unpublished events for the poller
        Index(
            "ix_outbox_status_created_at",
            "status",
            "created_at",
            postgresql_where="status = 'pending'",  # partial index
        ),
    )

    def __repr__(self) -> str:
        return f"<OutboxEvent id={self.id!r} type={self.event_type!r} status={self.status.value!r}>"
