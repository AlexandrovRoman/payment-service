from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from payment_service.db.base import Base


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"


class AggregateType(StrEnum):
    PAYMENT = "payment"


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    aggregate_type: Mapped[AggregateType] = mapped_column(
        Enum(
            AggregateType,
            name="aggregate_type_enum",
            inherit_schema=True,
            values_callable=lambda e: [field.value for field in e],
            create_type=False,
        ),
        nullable=False,
    )
    aggregate_id: Mapped[str] = mapped_column(String(26), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    routing_key: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[OutboxStatus] = mapped_column(
        Enum(
            OutboxStatus,
            name="outbox_status_enum",
            inherit_schema=True,
            values_callable=lambda e: [field.value for field in e],
            create_type=False,
        ),
        nullable=False,
        default=OutboxStatus.PENDING,
        server_default=OutboxStatus.PENDING.value,
    )

    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    attempts: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        # Index to efficiently find unpublished events for the poller
        Index(
            "ix_outbox_status_created_at",
            "status",
            "created_at",
            postgresql_where="status = 'pending'",
        ),
    )

    def __repr__(self) -> str:
        return f"<OutboxEvent id={self.id!r} type={self.event_type!r} status={self.status.value!r}>"
