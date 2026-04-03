from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict

from domain.enums import Currency, PaymentStatus


class CreatePaymentCommand(BaseModel):
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any] | None = None
    webhook_url: AnyHttpUrl
    idempotency_key: str


class PaymentDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any] | None
    status: PaymentStatus
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None
    failure_reason: str | None


class PaymentAcceptedDTO(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    created_at: datetime
