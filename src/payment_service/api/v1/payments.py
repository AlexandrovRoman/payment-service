"""Payment API endpoints.

POST /api/v1/payments   - create a payment (202 Accepted)
GET  /api/v1/payments/{payment_id} - get payment details
"""

import logging

from fastapi import APIRouter, Header, HTTPException, status

from payment_service.api.v1.schemas import (
    CreatePaymentRequest,
    CreatePaymentResponse,
    PaymentDetailResponse,
)
from payment_service.db.repositories import PaymentRepository
from payment_service.db.session import DbSession
from payment_service.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CreatePaymentResponse,
    summary="Create a payment",
)
async def create_payment(
    body: CreatePaymentRequest,
    db: DbSession,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> CreatePaymentResponse:
    """Accepts a payment creation request.

    - Validates the request body.
    - Deduplicates using the `Idempotency-Key` header.
    - Persists the payment and enqueues a processing event via Outbox.
    - Returns **202 Accepted** immediately; actual processing is async.
    """
    svc = PaymentService(db)
    return await svc.create_payment(
        idempotency_key=idempotency_key,
        amount=body.amount,
        currency=body.currency,
        description=body.description,
        metadata=body.metadata,
        webhook_url=body.webhook_url,
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentDetailResponse,
    summary="Get payment details",
)
async def get_payment(payment_id: str, db: DbSession) -> PaymentDetailResponse:
    """Return full details of a payment by its ID."""
    repo = PaymentRepository(db)
    payment = await repo.get_by_id(payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment '{payment_id}' not found",
        )
    return PaymentDetailResponse.model_validate(payment)
