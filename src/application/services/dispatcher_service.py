"""Фоновый dispatcher, публикующий события из outbox в RabbitMQ."""

from datetime import UTC, datetime

from application.services.outbox_service import schedule_outbox_retry
from core.logging import get_logger
from domain.enums import OutboxStatus
from infrastructure.broker.publisher import BrokerPublisher
from infrastructure.broker.schemas import PaymentCreatedMessage

logger = get_logger(__name__)


class OutboxDispatcherService:
    """Читает pending outbox-события и переводит их в published/failed."""

    def __init__(
        self,
        uow_factory,
        publisher: BrokerPublisher,
        batch_size: int,
        max_retries: int,
    ) -> None:
        self._uow_factory = uow_factory
        self._publisher = publisher
        self._batch_size = batch_size
        self._max_retries = max_retries

    async def dispatch_once(self) -> int:
        async with self._uow_factory() as uow:
            events = await uow.outbox.get_pending_batch(self._batch_size)
            if not events:
                return 0

            for event in events:
                try:
                    # Публикация выполняется вне HTTP-слоя.
                    # Это и есть ключевая часть Outbox Pattern: сначала commit в БД,
                    # потом гарантированная попытка публикации фоновой задачей.
                    await self._publisher.publish_payment_created(
                        PaymentCreatedMessage.model_validate(event.payload)
                    )
                    event.status = OutboxStatus.PUBLISHED
                    event.published_at = datetime.now(UTC)
                    event.next_retry_at = None
                    event.last_error = None
                except Exception as exc:
                    # При ошибке публикации запись не теряется:
                    # сохраняем текст ошибки и планируем следующую попытку.
                    logger.exception(
                        "outbox.publish_failed",
                        outbox_id=str(event.id),
                        aggregate_id=str(event.aggregate_id),
                    )
                    schedule_outbox_retry(event, str(exc), self._max_retries)

            await uow.commit()
            return len(events)
