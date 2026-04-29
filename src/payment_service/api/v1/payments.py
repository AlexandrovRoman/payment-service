import logging

from fastapi import APIRouter, Header, HTTPException, status

from payment_service.api.v1.schemas import (
    CreatePaymentRequest,
    CreatePaymentResponse,
    PaymentDetailResponse,
)
from payment_service.core.exceptions import PaymentNotFoundError
from payment_service.db.repositories import OutboxRepository, PaymentRepository
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
    svc = PaymentService(PaymentRepository(db), OutboxRepository(db))
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
    svc = PaymentService(PaymentRepository(db), OutboxRepository(db))
    try:
        payment = await svc.get_payment(payment_id)
    except PaymentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return payment
