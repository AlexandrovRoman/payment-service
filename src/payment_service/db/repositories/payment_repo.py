from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.db.models.payment import Currency, Payment, PaymentStatus


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_if_not_exists(
        self,
        *,
        payment_id: str,
        idempotency_key: str,
        amount: Decimal,
        currency: Currency,
        description: str | None = None,
        metadata: dict | None = None,
        webhook_url: str | None = None,
    ) -> Payment | None:
        """Persist a new payment in PENDING state."""
        stmt = (
            insert(Payment)
            .values(
                id=payment_id,
                idempotency_key=idempotency_key,
                amount=amount,
                currency=currency,
                description=description,
                metadata_=metadata,
                webhook_url=webhook_url,
                status=PaymentStatus.PENDING,
            )
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
            .returning(Payment)
        )

        result = await self._session.execute(stmt)
        payment = result.scalar_one_or_none()
        return payment

    async def get_by_id(self, payment_id: str) -> Payment | None:
        """Fetch a payment by its primary key."""
        result = await self._session.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        """Fetch a payment by idempotency key."""
        result = await self._session.execute(select(Payment).where(Payment.idempotency_key == key))
        return result.scalar_one_or_none()

    async def take_to_processing(self, payment_id: str) -> Payment | None:
        """Process a payment by its primary key."""
        result = await self._session.execute(
            update(Payment)
            .where(
                Payment.id == payment_id,
                Payment.status == PaymentStatus.PENDING,
            )
            .values(status=PaymentStatus.PROCESSING)
            .returning(Payment)
        )
        return result.scalar_one_or_none()

    async def rollback_to_pending(self, payment_id: str) -> Payment | None:
        result = await self._session.execute(
            update(Payment)
            .where(Payment.id == payment_id)
            .values(status=PaymentStatus.PENDING)
            .returning(Payment)
        )
        return result.scalar_one_or_none()

    async def update_status_if_pending(
        self,
        payment_id: str,
        status: PaymentStatus,
    ) -> Payment | None:
        result = await self._session.execute(
            update(Payment)
            .where(
                Payment.id == payment_id,
                Payment.status == PaymentStatus.PENDING,
            )
            .values(status=status, processed_at=datetime.now(UTC))
            .returning(Payment)
        )
        return result.scalar_one_or_none()
