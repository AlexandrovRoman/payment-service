"""Domain exceptions for the payment service."""


class PaymentServiceError(Exception):
    """Base exception for all payment service errors."""


class PaymentNotFoundError(PaymentServiceError):
    """Raised when a payment cannot be found by the given ID."""

    def __init__(self, payment_id: str) -> None:
        super().__init__(f"Payment '{payment_id}' not found")
        self.payment_id = payment_id


class DuplicateIdempotencyKeyError(PaymentServiceError):
    """Raised when a request with an already-used idempotency key arrives."""

    def __init__(self, key: str) -> None:
        super().__init__(f"Idempotency key '{key}' already used")
        self.key = key


class WebhookDeliveryError(PaymentServiceError):
    """Raised when webhook delivery permanently fails after all retries."""

    def __init__(self, url: str, attempts: int) -> None:
        super().__init__(f"Webhook to '{url}' failed after {attempts} attempts")
        self.url = url
        self.attempts = attempts
