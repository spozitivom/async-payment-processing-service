from collections.abc import Sequence
from typing import Protocol

from infrastructure.db.models.outbox import OutboxEvent


class OutboxRepository(Protocol):
    async def add(self, event: OutboxEvent) -> None: ...

    async def get_pending_batch(self, limit: int) -> Sequence[OutboxEvent]: ...
