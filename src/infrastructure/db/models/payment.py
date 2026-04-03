"""ORM-модель платежа."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.enums import Currency, PaymentStatus
from infrastructure.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class Payment(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Таблица платежей с состоянием обработки и данными для webhook."""

    __tablename__ = "payments"

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[Currency] = mapped_column(String(3), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    status: Mapped[PaymentStatus] = mapped_column(
        String(32), nullable=False, default=PaymentStatus.PENDING
    )
    # Уникальный ключ обеспечивает бизнес-идемпотентность и защищает от duplicate request race.
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    webhook_url: Mapped[str] = mapped_column(Text, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(nullable=True)
