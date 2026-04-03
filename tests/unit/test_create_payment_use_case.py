from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from application.dto.payments import CreatePaymentCommand
from application.use_cases.create_payment import CreatePaymentUseCase
from domain.enums import Currency, PaymentStatus
from infrastructure.db.models.payment import Payment


class FakePaymentsRepository:
    def __init__(self, payment: Payment | None) -> None:
        self._payment = payment

    async def get_by_idempotency_key(self, idempotency_key: str) -> Payment | None:
        return self._payment

    async def add(self, payment: Payment) -> None:
        self._payment = payment


class FakeOutboxRepository:
    async def add(self, event) -> None:
        return None


class FakeUnitOfWork:
    def __init__(self, payment: Payment | None) -> None:
        self.payments = FakePaymentsRepository(payment)
        self.outbox = FakeOutboxRepository()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def flush(self) -> None:
        return None


@pytest.mark.asyncio
async def test_create_payment_use_case_returns_existing_payment_on_idempotency_hit() -> None:
    existing_payment = Payment(
        id=uuid4(),
        amount=Decimal("10.00"),
        currency=Currency.USD,
        description="Existing payment",
        metadata_json={"order_id": "1"},
        status=PaymentStatus.PENDING,
        idempotency_key="idem-1",
        webhook_url="https://example.com/webhook",
        created_at=datetime.now(UTC),
    )
    use_case = CreatePaymentUseCase(lambda: FakeUnitOfWork(existing_payment))

    result = await use_case.execute(
        CreatePaymentCommand(
            amount=Decimal("10.00"),
            currency=Currency.USD,
            description="Existing payment",
            metadata={"order_id": "1"},
            webhook_url="https://example.com/webhook",
            idempotency_key="idem-1",
        )
    )

    assert result.payment_id == existing_payment.id
    assert result.status == PaymentStatus.PENDING
