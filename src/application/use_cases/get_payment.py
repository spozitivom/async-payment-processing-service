"""Use case чтения платежа по идентификатору."""

from collections.abc import Callable
from uuid import UUID

from application.dto.payments import PaymentDTO
from core.exceptions import PaymentNotFoundError
from infrastructure.db.uow import AbstractUnitOfWork


class GetPaymentUseCase:
    """Изолирует чтение платежа от HTTP-слоя и инфраструктурных деталей."""

    def __init__(self, uow_factory: Callable[[], AbstractUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, payment_id: UUID) -> PaymentDTO:
        async with self._uow_factory() as uow:
            payment = await uow.payments.get_by_id(payment_id)
            if payment is None:
                raise PaymentNotFoundError(f"Payment {payment_id} not found")

            return PaymentDTO(
                id=payment.id,
                amount=payment.amount,
                currency=payment.currency,
                description=payment.description,
                metadata=payment.metadata_json,
                status=payment.status,
                idempotency_key=payment.idempotency_key,
                webhook_url=payment.webhook_url,
                created_at=payment.created_at,
                processed_at=payment.processed_at,
                failure_reason=payment.failure_reason,
            )
