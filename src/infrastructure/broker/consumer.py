"""Конфигурация RabbitMQ consumer для событий о новых платежах."""

from core.logging import get_logger
from infrastructure.broker.schemas import PaymentCreatedMessage
from infrastructure.broker.topology import broker, payments_exchange, payments_queue

logger = get_logger(__name__)
_handler = None


def configure_payment_consumer(handler) -> None:
    """Связывает подписчик брокера с application-сервисом обработки платежей."""

    global _handler
    _handler = handler


@broker.subscriber(payments_queue, payments_exchange)
async def handle_payment_created(message: PaymentCreatedMessage) -> None:
    """Принимает сообщение из RabbitMQ и передает обработку в application-слой."""

    if _handler is None:
        raise RuntimeError("Payment consumer handler is not configured")
    logger.info("broker.payment_message_received", payment_id=str(message.payment_id))
    await _handler.process(message.payment_id)
