from datetime import UTC, datetime
from uuid import uuid4

import pytest

from application.services.dispatcher_service import OutboxDispatcherService
from domain.enums import OutboxStatus
from infrastructure.db.models.outbox import OutboxEvent


class FakeOutboxRepository:
    def __init__(self, events: list[OutboxEvent]) -> None:
        self._events = events

    async def get_pending_batch(self, limit: int) -> list[OutboxEvent]:
        return self._events[:limit]


class FakeUnitOfWork:
    def __init__(self, events: list[OutboxEvent]) -> None:
        self.outbox = FakeOutboxRepository(events)
        self._committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def commit(self) -> None:
        self._committed = True


class FakePublisher:
    def __init__(self) -> None:
        self.published: list[str] = []

    async def publish_payment_created(self, message) -> None:
        self.published.append(str(message.payment_id))


@pytest.mark.asyncio
async def test_dispatcher_marks_outbox_event_as_published() -> None:
    event = OutboxEvent(
        id=uuid4(),
        aggregate_type="payment",
        aggregate_id=uuid4(),
        event_type="payment.created",
        payload={"payment_id": str(uuid4())},
        status=OutboxStatus.PENDING,
        retry_count=0,
        created_at=datetime.now(UTC),
    )
    publisher = FakePublisher()
    service = OutboxDispatcherService(
        uow_factory=lambda: FakeUnitOfWork([event]),
        publisher=publisher,
        batch_size=10,
        max_retries=5,
    )

    dispatched = await service.dispatch_once()

    assert dispatched == 1
    assert event.status == OutboxStatus.PUBLISHED
    assert event.published_at is not None
    assert publisher.published == [event.payload["payment_id"]]
