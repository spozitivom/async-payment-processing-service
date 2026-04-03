"""Unit of Work для централизованного управления транзакцией SQLAlchemy."""

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from domain.repositories.outbox import OutboxRepository
from domain.repositories.payment import PaymentRepository
from infrastructure.db import session as db_session
from infrastructure.db.repositories.outbox import SqlAlchemyOutboxRepository
from infrastructure.db.repositories.payment import SqlAlchemyPaymentRepository


class AbstractUnitOfWork(Protocol):
    """Контракт UoW, который используют use case и application-сервисы."""

    payments: PaymentRepository
    outbox: OutboxRepository

    async def __aenter__(self) -> "AbstractUnitOfWork": ...

    async def __aexit__(self, exc_type, exc, tb) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def flush(self) -> None: ...


class SqlAlchemyUnitOfWork:
    """Инкапсулирует session lifecycle, repositories и commit/rollback."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self._session_factory = session_factory or db_session.SessionFactory
        self.session: AsyncSession | None = None
        self.payments: SqlAlchemyPaymentRepository
        self.outbox: SqlAlchemyOutboxRepository

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        # Use case не должен сам собирать repositories и управлять session вручную.
        self.session = self._session_factory()
        self.payments = SqlAlchemyPaymentRepository(self.session)
        self.outbox = SqlAlchemyOutboxRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.session is None:
            return
        if exc_type is not None:
            # При любой ошибке транзакция откатывается в одном месте.
            await self.rollback()
        await self.session.close()

    async def commit(self) -> None:
        if self.session is None:
            return
        await self.session.commit()

    async def rollback(self) -> None:
        if self.session is None:
            return
        await self.session.rollback()

    async def flush(self) -> None:
        if self.session is None:
            return
        await self.session.flush()
