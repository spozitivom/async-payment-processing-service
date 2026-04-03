"""Описание RabbitMQ topology для основного потока платежей и DLQ."""

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
    """Явно объявляет exchange/queue и их binding при старте worker."""

    main_exchange = await broker.declare_exchange(payments_exchange)
    dlx_exchange = await broker.declare_exchange(payments_dlx)
    main_queue = await broker.declare_queue(payments_queue)
    dlq_queue = await broker.declare_queue(payments_dlq)

    # Явно связываем очереди с exchange, чтобы topology не зависела
    # от наличия subscriber-ов и корректно работала для DLQ.
    await main_queue.bind(main_exchange, routing_key=payments_routing_key)
    await dlq_queue.bind(dlx_exchange, routing_key=payments_dlq.name)
