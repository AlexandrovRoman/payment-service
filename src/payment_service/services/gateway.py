"""Payment gateway emulator.

Simulates an external payment processor:
- Random delay between 2-5 seconds
- 90% success / 10% failure probability
"""

import asyncio
import logging
import random

from payment_service.core.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GatewayResult:
    """Outcome of a gateway call."""

    __slots__ = ("message", "success")

    def __init__(self, *, success: bool, message: str) -> None:
        self.success = success
        self.message = message


async def process_payment(payment_id: str, amount: str, currency: str) -> GatewayResult:
    """Emulate calling an external payment gateway.

    Args:
        payment_id: The unique identifier of the payment.
        amount:     Decimal amount as a string.
        currency:   ISO 4217 currency code.

    Returns:
        GatewayResult with success=True or False.
    """
    delay = random.uniform(settings.gateway_min_delay, settings.gateway_max_delay)  # noqa: S311
    logger.debug(
        "Gateway processing payment",
        extra={"payment_id": payment_id, "delay": round(delay, 2)},
    )
    await asyncio.sleep(delay)

    success = random.random() < settings.gateway_success_rate  # noqa: S311
    if success:
        logger.info("Gateway approved payment", extra={"payment_id": payment_id})
        return GatewayResult(success=True, message="approved")
    else:
        logger.warning("Gateway declined payment", extra={"payment_id": payment_id})
        return GatewayResult(success=False, message="declined_by_gateway")
