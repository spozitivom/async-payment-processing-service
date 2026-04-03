from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from core.config import get_settings

settings = get_settings()

payments_exchange = RabbitExchange(
    settings.payments_exchange,
    type=ExchangeType.DIRECT,
    durable=True,
)
payments_queue = RabbitQueue(
    settings.payments_queue,
    durable=True,
    routing_key=settings.payments_routing_key,
)
payments_dlx = RabbitExchange(
    settings.payments_dlx,
    type=ExchangeType.DIRECT,
    durable=True,
)
payments_dlq = RabbitQueue(
    settings.payments_dlq,
    durable=True,
    routing_key=settings.payments_dlq,
)

broker = RabbitBroker(settings.rabbitmq_url)
payments_routing_key = settings.payments_routing_key


async def declare_topology() -> None:
    await broker.declare_exchange(payments_exchange)
    await broker.declare_exchange(payments_dlx)
    await broker.declare_queue(payments_queue)
    await broker.declare_queue(payments_dlq)
