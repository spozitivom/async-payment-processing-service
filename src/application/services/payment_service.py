"""Сервис обработки платежа в consumer и запуска webhook delivery."""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from core.logging import get_logger
from domain.enums import PaymentStatus
from infrastructure.broker.publisher import BrokerPublisher
from infrastructure.broker.schemas import PaymentWebhookFailedMessage
from infrastructure.db.models.payment import Payment
from infrastructure.db.uow import AbstractUnitOfWork

logger = get_logger(__name__)


class PaymentProcessingService:
    """Инкапсулирует consumer flow: обработка платежа, webhook и DLQ."""

    def __init__(
        self,
        uow_factory: Callable[[], AbstractUnitOfWork],
        gateway,
        webhook_service,
        publisher: BrokerPublisher,
    ) -> None:
        self._uow_factory = uow_factory
        self._gateway = gateway
        self._webhook_service = webhook_service
        self._publisher = publisher

    async def process(self, payment_id: UUID) -> None:
        # Повторная обработка сообщения не должна повторно "финализировать" платеж:
        # если статус уже не pending, consumer завершает работу без побочных эффектов.
        async with self._uow_factory() as uow:
            payment = await uow.payments.get_by_id(payment_id)
            if payment is None:
                logger.warning("payment.consumer_missing_payment", payment_id=str(payment_id))
                return

            if payment.status == PaymentStatus.PENDING:
                logger.info("payment.consumer_processing_started", payment_id=str(payment_id))
                payment.status, payment.failure_reason = await self._gateway.process()
                payment.processed_at = datetime.now(UTC)
                await uow.commit()
                logger.info(
                    "payment.consumer_processing_completed",
                    payment_id=str(payment_id),
                    status=payment.status,
                )
            else:
                logger.info(
                    "payment.consumer_already_finalized",
                    payment_id=str(payment_id),
                    status=payment.status,
                )

        # Webhook отправляется уже после фиксации финального статуса платежа,
        # чтобы внешний получатель видел консистентное состояние.
        await self._deliver_webhook(payment)

    async def _deliver_webhook(self, payment: Payment) -> None:
        """Пытается доставить webhook и при окончательном провале публикует событие в DLQ."""

        payload = {
            "payment_id": str(payment.id),
            "status": payment.status,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "description": payment.description,
            "metadata": payment.metadata_json,
            "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
            "failure_reason": payment.failure_reason,
        }
        result = await self._webhook_service.deliver(payment.webhook_url, payload)
        if result.delivered:
            return

        # DLQ flow нужен для ручного разбора случаев,
        # когда webhook не удалось доставить даже после retry.
        await self._publisher.publish_webhook_failed(
            PaymentWebhookFailedMessage(
                payment_id=payment.id,
                status=payment.status,
                amount=payment.amount,
                currency=payment.currency,
                description=payment.description,
                metadata=payment.metadata_json,
                processed_at=payment.processed_at,
                failure_reason=payment.failure_reason,
                webhook_url=payment.webhook_url,
                webhook_error=result.last_error,
            )
        )
