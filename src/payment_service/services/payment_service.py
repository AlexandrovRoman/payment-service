"""Payment service - orchestrates the create-payment use case.

Responsibilities:
- Generate payment ID (ULID)
- Check idempotency key for duplicates
- Persist Payment + OutboxEvent in a single transaction
"""

import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from payment_service.api.v1.schemas import (
    CreatePaymentResponse,
    PaymentCreatedEvent,
)
from payment_service.core.settings import get_settings
from payment_service.db.models.payment import Currency
from payment_service.db.repositories import OutboxRepository, PaymentRepository

logger = logging.getLogger(__name__)
settings = get_settings()


class PaymentService:
    """Application service for the Payment aggregate."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._payment_repo = PaymentRepository(session)
        self._outbox_repo = OutboxRepository(session)

    async def create_payment(
        self,
        *,
        idempotency_key: str,
        amount: Decimal,
        currency: Currency,
        description: str | None = None,
        metadata: dict | None = None,
        webhook_url: str | None = None,
    ) -> CreatePaymentResponse:
        """Create a new payment and enqueue it via the Outbox pattern.

        Returns the existing payment response if the idempotency key
        was already used (safe retry).

        Raises:
            DuplicateIdempotencyKeyError: theoretically unreachable due to
                the safe-return path, but kept for explicit contract.
        """
        # --- Idempotency check ---
        existing = await self._payment_repo.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            logger.info(
                "Idempotency key already used, returning existing payment",
                extra={"payment_id": existing.id, "idempotency_key": idempotency_key},
            )
            return CreatePaymentResponse(
                payment_id=existing.id,
                status=existing.status,
                created_at=existing.created_at,
            )

        payment_id = str(ULID())
        event_id = str(ULID())

        # --- Persist payment ---
        payment = await self._payment_repo.create(
            payment_id=payment_id,
            idempotency_key=idempotency_key,
            amount=amount,
            currency=currency,
            description=description,
            metadata=metadata,
            webhook_url=str(webhook_url) if webhook_url else None,
        )

        # --- Write outbox event (same transaction) ---
        event_payload = PaymentCreatedEvent(
            payment_id=payment_id,
            amount=str(amount),
            currency=currency.value,
            webhook_url=str(webhook_url) if webhook_url else None,
        )
        await self._outbox_repo.create_event(
            event_id=event_id,
            aggregate_type="payment",
            aggregate_id=payment_id,
            event_type="payment.created",
            payload=event_payload.model_dump(),
            routing_key=settings.payments_new_queue,
        )

        logger.info(
            "Payment created",
            extra={"payment_id": payment_id, "currency": currency.value},
        )

        return CreatePaymentResponse(
            payment_id=payment.id,
            status=payment.status,
            created_at=payment.created_at,
        )
