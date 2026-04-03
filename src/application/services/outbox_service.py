from datetime import UTC, datetime, timedelta

from domain.enums import OutboxStatus
from infrastructure.db.models.outbox import OutboxEvent


def calculate_exponential_backoff(attempt: int) -> int:
    return 2 ** max(attempt - 1, 0)


def schedule_outbox_retry(event: OutboxEvent, error: str, max_retries: int) -> None:
    event.retry_count += 1
    event.last_error = error
    if event.retry_count >= max_retries:
        event.status = OutboxStatus.FAILED
        return

    delay = calculate_exponential_backoff(event.retry_count)
    event.next_retry_at = datetime.now(UTC) + timedelta(seconds=delay)
