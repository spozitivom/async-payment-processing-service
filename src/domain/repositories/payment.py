from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from infrastructure.db.models.payment import Payment


class PaymentRepository(Protocol):
    async def add(self, payment: Payment) -> None: ...

    async def get_by_id(self, payment_id: UUID) -> Payment | None: ...

    async def get_by_idempotency_key(self, idempotency_key: str) -> Payment | None: ...

    async def list_all(self) -> Sequence[Payment]: ...
