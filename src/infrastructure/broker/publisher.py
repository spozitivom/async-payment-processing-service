from core.logging import get_logger
from infrastructure.broker.schemas import PaymentCreatedMessage, PaymentWebhookFailedMessage
from infrastructure.broker.topology import (
    broker,
    payments_dlq,
    payments_dlx,
    payments_exchange,
    payments_routing_key,
)

logger = get_logger(__name__)


class BrokerPublisher:
    async def publish_payment_created(self, message: PaymentCreatedMessage) -> None:
        await broker.publish(
            message,
            exchange=payments_exchange,
            routing_key=payments_routing_key,
            persist=True,
        )
        logger.info("broker.payment_created_published", payment_id=str(message.payment_id))

    async def publish_webhook_failed(self, message: PaymentWebhookFailedMessage) -> None:
        await broker.publish(
            message,
            exchange=payments_dlx,
            routing_key=payments_dlq.name,
            persist=True,
        )
        logger.warning("broker.webhook_failed_published_dlq", payment_id=str(message.payment_id))
