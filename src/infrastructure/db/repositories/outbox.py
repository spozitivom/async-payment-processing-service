from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import OutboxStatus
from infrastructure.db.models.outbox import OutboxEvent


class SqlAlchemyOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: OutboxEvent) -> None:
        self._session.add(event)

    async def get_pending_batch(self, limit: int) -> Sequence[OutboxEvent]:
        now = datetime.now(UTC)
        stmt = (
            select(OutboxEvent)
            .where(OutboxEvent.status == OutboxStatus.PENDING)
            .where(or_(OutboxEvent.next_retry_at.is_(None), OutboxEvent.next_retry_at <= now))
            .order_by(OutboxEvent.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await self._session.scalars(stmt)).all())
