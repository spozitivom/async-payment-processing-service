from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from domain.enums import Currency, PaymentStatus


class PaymentCreatedMessage(BaseModel):
    payment_id: UUID


class PaymentWebhookFailedMessage(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any] | None
    processed_at: datetime | None
    failure_reason: str | None
    webhook_url: str
    webhook_error: str | None
