"""Pydantic v2 request/response schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from payment_service.db.models.payment import Currency, PaymentStatus

# ── Request schemas ───────────────────────────────────────────────────────────


class CreatePaymentRequest(BaseModel):
    """Body of POST /api/v1/payments."""

    model_config = ConfigDict(str_strip_whitespace=True)

    amount: Decimal = Field(gt=0, decimal_places=2, description="Payment amount")
    currency: Currency
    description: str | None = Field(default=None, max_length=500)
    metadata: dict | None = None
    webhook_url: HttpUrl | None = None


# ── Response schemas ──────────────────────────────────────────────────────────


class CreatePaymentResponse(BaseModel):
    """202 Accepted response for POST /api/v1/payments."""

    payment_id: str
    status: PaymentStatus
    created_at: datetime


class PaymentDetailResponse(BaseModel):
    """Full payment details for GET /api/v1/payments/{payment_id}."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    payment_id: str = Field(serialization_alias="payment_id", validation_alias="id")
    idempotency_key: str
    amount: Decimal
    currency: Currency
    description: str | None
    metadata: dict | None = Field(None, alias="metadata_")
    webhook_url: str | None
    status: PaymentStatus
    created_at: datetime
    processed_at: datetime | None

    @field_validator("payment_id", mode="before")
    @classmethod
    def coerce_id(cls, v: object) -> object:
        return v


# ── Messaging schemas ─────────────────────────────────────────────────────────


class PaymentCreatedEvent(BaseModel):
    """Event payload published to payments.new queue."""

    payment_id: str
    amount: str  # Decimal serialised as string for safe JSON transport
    currency: str
    webhook_url: str | None


class WebhookPayload(BaseModel):
    """Payload delivered to the client's webhook URL."""

    payment_id: str
    status: PaymentStatus
    amount: Decimal
    currency: Currency
    processed_at: datetime | None
