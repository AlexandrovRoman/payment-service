"""RabbitMQ broker configuration using FastStream.

Topology:
  payments exchange (direct)
      └── payments.new queue
              └── DLX: payments.dlx  →  payments.new.dlq (after 3 nacks)

The Dead Letter Exchange (DLX) is set as a queue argument so RabbitMQ
automatically routes messages to the DLQ when they are rejected/nacked
more than `x-delivery-count` times (handled in the consumer).
"""

from faststream.rabbit import (
    ExchangeType,
    RabbitBroker,
    RabbitExchange,
    RabbitQueue,
)

from payment_service.core.settings import get_settings

settings = get_settings()

# ── Broker ────────────────────────────────────────────────────────────────────
broker = RabbitBroker(str(settings.rabbitmq_url))

# ── Exchanges ─────────────────────────────────────────────────────────────────
payments_exchange = RabbitExchange(
    name=settings.payments_exchange,
    type=ExchangeType.DIRECT,
    durable=True,
)

# Dead-letter exchange: receives messages rejected after max retries
dlx_exchange = RabbitExchange(
    name=settings.payments_dlx,
    type=ExchangeType.FANOUT,
    durable=True,
)

# ── Queues ────────────────────────────────────────────────────────────────────
payments_new_queue = RabbitQueue(
    name=settings.payments_new_queue,
    durable=True,
    arguments={
        # Route rejected messages to the DLX
        "x-dead-letter-exchange": settings.payments_dlx,
    },
)

payments_dlq = RabbitQueue(
    name=settings.payments_dlq,
    durable=True,
    # DLQ is bound to the DLX with no routing key (fanout)
)
