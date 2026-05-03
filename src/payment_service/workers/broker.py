from faststream.rabbit import ExchangeType, QueueType, RabbitBroker, RabbitExchange, RabbitQueue
from faststream.rabbit.schemas.queue import QuorumQueueArgs

from payment_service.core.settings import settings

broker = RabbitBroker(str(settings.rabbitmq_url))

payments_exchange = RabbitExchange(
    name=settings.payments_exchange,
    type=ExchangeType.TOPIC,
    durable=True,
)

payments_dlx = RabbitExchange(
    name=f"{settings.payments_exchange}.dlx",
    type=ExchangeType.FANOUT,
    durable=True,
)

payments_new_queue = RabbitQueue(
    name=settings.payments_new_queue,
    durable=True,
    routing_key=settings.payments_new_queue,
    queue_type=QueueType.QUORUM,
    arguments=QuorumQueueArgs(
        **{
            "x-dead-letter-exchange": f"{settings.payments_exchange}.dlx",
            "x-delivery-limit": settings.max_retry_attempts,
        }
    ),
)

payments_dlq = RabbitQueue(
    name="payments.dlq",
    durable=True,
    queue_type=QueueType.QUORUM,
)
