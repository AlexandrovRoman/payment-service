"""Payment repository - data access layer for Payment entities."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.db.models.payment import Currency, Payment, PaymentStatus


class PaymentRepository:
    """All database operations related to the Payment aggregate."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        payment_id: str,
        idempotency_key: str,
        amount: Decimal,
        currency: Currency,
        description: str | None = None,
        metadata: dict | None = None,
        webhook_url: str | None = None,
    ) -> Payment:
        """Persist a new payment in PENDING state."""
        payment = Payment(
            id=payment_id,
            idempotency_key=idempotency_key,
            amount=amount,
            currency=currency,
            description=description,
            metadata_=metadata,
            webhook_url=webhook_url,
            status=PaymentStatus.PENDING,
        )
        self._session.add(payment)
        await self._session.flush()  # assigns server defaults without committing
        return payment

    async def get_by_id(self, payment_id: str) -> Payment | None:
        """Fetch a payment by its primary key."""
        result = await self._session.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        """Fetch a payment by idempotency key."""
        result = await self._session.execute(select(Payment).where(Payment.idempotency_key == key))
        return result.scalar_one_or_none()

    async def update_status(
        self,
        payment: Payment,
        status: PaymentStatus,
    ) -> Payment:
        """Update payment status and set processed_at timestamp."""
        payment.status = status
        payment.processed_at = datetime.now(UTC)
        await self._session.flush()
        return payment
