from faststream.rabbit import (
    ExchangeType,
    RabbitBroker,
    RabbitExchange,
    RabbitQueue,
)

from payment_service.core.settings import settings

broker = RabbitBroker(str(settings.rabbitmq_url))

payments_exchange = RabbitExchange(
    name=settings.payments_exchange,
    type=ExchangeType.TOPIC,
    durable=True,
)

payments_new_queue = RabbitQueue(
    name=settings.payments_new_queue,
    durable=True,
    routing_key=settings.payments_new_queue,
)

payments_dlq_queue = RabbitQueue(
    name="payments.dlq",
    durable=True,
    routing_key="payments.#.dlq",
)
