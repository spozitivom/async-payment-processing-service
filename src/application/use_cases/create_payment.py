"""Use case создания платежа с идемпотентностью и атомарной записью в outbox."""

from collections.abc import Callable
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from application.dto.payments import CreatePaymentCommand, PaymentAcceptedDTO
from core.logging import get_logger
from domain.enums import OutboxStatus, PaymentStatus
from infrastructure.db.models.outbox import OutboxEvent
from infrastructure.db.models.payment import Payment
from infrastructure.db.uow import AbstractUnitOfWork

logger = get_logger(__name__)


class CreatePaymentUseCase:
    """Создает платеж и outbox-событие в рамках одной транзакции."""

    def __init__(self, uow_factory: Callable[[], AbstractUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, command: CreatePaymentCommand) -> PaymentAcceptedDTO:
        async with self._uow_factory() as uow:
            # Быстрый путь идемпотентности: если ключ уже использован,
            # возвращаем существующий платеж без новых записей.
            existing = await uow.payments.get_by_idempotency_key(command.idempotency_key)
            if existing is not None:
                logger.info(
                    "payment.idempotency_hit",
                    payment_id=str(existing.id),
                    idempotency_key=command.idempotency_key,
                )
                return PaymentAcceptedDTO(
                    payment_id=existing.id,
                    status=existing.status,
                    created_at=existing.created_at,
                )

            payment_id = uuid4()

            payment = Payment(
                id=payment_id,
                amount=command.amount,
                currency=command.currency,
                description=command.description,
                metadata_json=command.metadata,
                status=PaymentStatus.PENDING,
                idempotency_key=command.idempotency_key,
                webhook_url=str(command.webhook_url),
            )

            await uow.payments.add(payment)
            await uow.outbox.add(
                OutboxEvent(
                    aggregate_type="payment",
                    aggregate_id=payment_id,
                    event_type="payment.created",
                    payload={"payment_id": str(payment_id)},
                    status=OutboxStatus.PENDING,
                )
            )
            # Flush нужен до commit, чтобы все изменения были синхронизированы с сессией
            # и возможные ошибки ограничений проявились внутри текущего UoW.
            await uow.flush()

            try:
                await uow.commit()
            except IntegrityError:
                # Защита от гонки duplicate request race:
                # если два одинаковых запроса пришли почти одновременно,
                # уникальный индекс сохранит только один платеж.
                await uow.rollback()
                existing = await uow.payments.get_by_idempotency_key(command.idempotency_key)
                if existing is None:
                    raise
                return PaymentAcceptedDTO(
                    payment_id=existing.id,
                    status=existing.status,
                    created_at=existing.created_at,
                )

            logger.info(
                "payment.created",
                payment_id=str(payment.id),
                idempotency_key=command.idempotency_key,
            )
            return PaymentAcceptedDTO(
                payment_id=payment_id,
                status=payment.status,
                created_at=payment.created_at,
            )
