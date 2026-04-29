import logging
from decimal import Decimal

from ulid import ULID

from payment_service.api.v1.schemas import (
    CreatePaymentResponse,
    PaymentCreatedEvent,
    PaymentDetailResponse,
)
from payment_service.core.exceptions import PaymentNotFoundError
from payment_service.core.settings import settings
from payment_service.db.models.payment import Currency
from payment_service.db.repositories import OutboxRepository, PaymentRepository

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, payment_repo: PaymentRepository, outbox_repo: OutboxRepository) -> None:
        self._payment_repo = payment_repo
        self._outbox_repo = outbox_repo

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
        payment_id = str(ULID())
        event_id = str(ULID())

        payment = await self._payment_repo.create_if_not_exists(
            payment_id=payment_id,
            idempotency_key=idempotency_key,
            amount=amount,
            currency=currency,
            description=description,
            metadata=metadata,
            webhook_url=str(webhook_url) if webhook_url else None,
        )

        if not payment:
            payment = await self._payment_repo.get_by_idempotency_key(idempotency_key)
            return CreatePaymentResponse(
                payment_id=payment.id,
                status=payment.status,
                created_at=payment.created_at,
            )

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

    async def get_payment(self, payment_id: str) -> PaymentDetailResponse:
        payment = await self._payment_repo.get_by_id(payment_id)
        if payment is None:
            raise PaymentNotFoundError(payment_id)
        return PaymentDetailResponse.model_validate(payment, from_attributes=True)
