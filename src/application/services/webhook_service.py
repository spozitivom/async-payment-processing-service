"""Retry-логика доставки webhook."""

import asyncio
from dataclasses import dataclass
from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class WebhookDeliveryResult:
    """Результат доставки webhook после всех попыток."""

    delivered: bool
    attempts: int
    last_error: str | None = None


class WebhookService:
    """Делает ограниченное количество попыток отправки webhook с exponential backoff."""

    def __init__(self, client: Any, max_retries: int) -> None:
        self._client = client
        self._max_retries = max_retries

    async def deliver(self, url: str, payload: dict[str, Any]) -> WebhookDeliveryResult:
        last_error: str | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                await self._client.post_json(url, payload)
                logger.info("webhook.delivered", webhook_url=url, attempt=attempt)
                return WebhookDeliveryResult(delivered=True, attempts=attempt)
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "webhook.retry",
                    webhook_url=url,
                    attempt=attempt,
                    max_retries=self._max_retries,
                    error=last_error,
                )
                if attempt < self._max_retries:
                    # Базовая экспоненциальная задержка: 1s, 2s, 4s.
                    await asyncio.sleep(2 ** (attempt - 1))

        return WebhookDeliveryResult(
            delivered=False,
            attempts=self._max_retries,
            last_error=last_error,
        )
