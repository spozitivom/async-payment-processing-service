from application.services.outbox_service import calculate_exponential_backoff


def test_calculate_exponential_backoff() -> None:
    assert calculate_exponential_backoff(1) == 1
    assert calculate_exponential_backoff(2) == 2
    assert calculate_exponential_backoff(3) == 4
