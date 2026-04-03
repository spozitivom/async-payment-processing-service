import asyncio

from application.services.dispatcher_service import OutboxDispatcherService
from core.logging import get_logger

logger = get_logger(__name__)


async def run_outbox_dispatcher(service: OutboxDispatcherService, poll_interval: int) -> None:
    while True:
        dispatched = await service.dispatch_once()
        if dispatched:
            logger.info("outbox.batch_dispatched", count=dispatched)
        await asyncio.sleep(poll_interval)
