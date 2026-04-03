"""Entrypoint worker-процесса: outbox dispatcher + RabbitMQ consumer."""

import asyncio
from contextlib import suppress

from application.services.dispatcher_service import OutboxDispatcherService
from application.services.payment_service import PaymentProcessingService
from application.services.processing_service import PaymentGatewaySimulator
from application.services.webhook_service import WebhookService
from core.config import get_settings
from core.logging import configure_logging, get_logger
from infrastructure.broker.consumer import configure_payment_consumer
from infrastructure.broker.publisher import BrokerPublisher
from infrastructure.broker.topology import broker, declare_topology
from infrastructure.clients.webhook_client import WebhookClient
from infrastructure.db.uow import SqlAlchemyUnitOfWork
from workers.outbox_dispatcher import run_outbox_dispatcher

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


async def main() -> None:
    # Один worker-process сознательно объединяет dispatcher и consumer.
    # Для тестового это упрощает запуск и демонстрирует полный async flow.
    webhook_client = WebhookClient(timeout_seconds=settings.webhook_timeout_seconds)
    publisher = BrokerPublisher()
    processing_service = PaymentProcessingService(
        uow_factory=SqlAlchemyUnitOfWork,
        gateway=PaymentGatewaySimulator(),
        webhook_service=WebhookService(
            client=webhook_client,
            max_retries=settings.webhook_max_retries,
        ),
        publisher=publisher,
    )
    dispatcher_service = OutboxDispatcherService(
        uow_factory=SqlAlchemyUnitOfWork,
        publisher=publisher,
        batch_size=settings.outbox_batch_size,
        max_retries=settings.outbox_max_retries,
    )

    configure_payment_consumer(processing_service)

    await broker.start()
    await declare_topology()
    # Dispatcher работает циклически параллельно с consumer lifecycle брокера.
    dispatcher_task = asyncio.create_task(
        run_outbox_dispatcher(dispatcher_service, settings.outbox_poll_interval)
    )

    logger.info("worker.started")
    try:
        await asyncio.Event().wait()
    finally:
        dispatcher_task.cancel()
        with suppress(asyncio.CancelledError):
            await dispatcher_task
        await webhook_client.close()
        await broker.close()
        logger.info("worker.stopped")


if __name__ == "__main__":
    asyncio.run(main())
