"""Payment ORM model."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Enum, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from payment_service.db.base import Base


class Currency(StrEnum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Payment(Base):
    """Represents a single payment transaction."""

    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    """ULID-based unique identifier."""

    idempotency_key: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    """Client-supplied key for deduplication."""

    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[Currency] = mapped_column(Enum(Currency, name="currency_enum"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    webhook_url: Mapped[str | None] = mapped_column(Text)

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status_enum"),
        nullable=False,
        default=PaymentStatus.PENDING,
        server_default=PaymentStatus.PENDING.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_payments_status_created_at", "status", "created_at"),)

    def __repr__(self) -> str:
        return (
            f"<Payment id={self.id!r} status={self.status.value!r} "
            f"amount={self.amount} {self.currency.value}>"
        )
