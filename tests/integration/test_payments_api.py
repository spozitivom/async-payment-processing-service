"""Интеграционные тесты HTTP-контрактов для payments API."""

from sqlalchemy import func, select

from infrastructure.db.models.outbox import OutboxEvent
from infrastructure.db.models.payment import Payment


async def test_create_payment_creates_payment_and_outbox(client) -> None:
    """Новый POST должен создать и сам платеж, и outbox-событие в одной транзакции."""

    response = await client.post(
        "/api/v1/payments",
        headers={"X-API-Key": "test-api-key", "Idempotency-Key": "idem-1"},
        json={
            "amount": "100.00",
            "currency": "USD",
            "description": "Order #1",
            "metadata": {"order_id": "1"},
            "webhook_url": "https://example.com/webhook",
        },
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    assert data["payment_id"]

    from infrastructure.db import session as session_module

    async with session_module.SessionFactory() as session:
        payments_count = await session.scalar(select(func.count()).select_from(Payment))
        outbox_count = await session.scalar(select(func.count()).select_from(OutboxEvent))
        assert payments_count == 1
        assert outbox_count == 1


async def test_create_payment_is_idempotent(client) -> None:
    """Повторный POST с тем же ключом не должен создавать дубли ни в payments, ни в outbox."""

    payload = {
        "amount": "100.00",
        "currency": "USD",
        "description": "Order #1",
        "metadata": {"order_id": "1"},
        "webhook_url": "https://example.com/webhook",
    }

    first = await client.post(
        "/api/v1/payments",
        headers={"X-API-Key": "test-api-key", "Idempotency-Key": "idem-2"},
        json=payload,
    )
    second = await client.post(
        "/api/v1/payments",
        headers={"X-API-Key": "test-api-key", "Idempotency-Key": "idem-2"},
        json=payload,
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["payment_id"] == second.json()["payment_id"]
    assert first.json()["status"] == "pending"
    assert second.json()["status"] == "pending"

    from infrastructure.db import session as session_module

    async with session_module.SessionFactory() as session:
        payments_count = await session.scalar(select(func.count()).select_from(Payment))
        outbox_count = await session.scalar(select(func.count()).select_from(OutboxEvent))
        assert payments_count == 1
        assert outbox_count == 1


async def test_get_payment_returns_existing_payment(client) -> None:
    """GET должен вернуть полный контракт платежа после успешного создания."""

    create_response = await client.post(
        "/api/v1/payments",
        headers={"X-API-Key": "test-api-key", "Idempotency-Key": "idem-get-1"},
        json={
            "amount": "150.75",
            "currency": "EUR",
            "description": "Order #GET",
            "metadata": {"source": "integration-test"},
            "webhook_url": "https://example.com/webhook",
        },
    )
    payment_id = create_response.json()["payment_id"]

    response = await client.get(
        f"/api/v1/payments/{payment_id}",
        headers={"X-API-Key": "test-api-key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == payment_id
    assert data["amount"] == "150.75"
    assert data["currency"] == "EUR"
    assert data["description"] == "Order #GET"
    assert data["metadata"] == {"source": "integration-test"}
    assert data["status"] == "pending"
    assert data["idempotency_key"] == "idem-get-1"
    assert data["webhook_url"] == "https://example.com/webhook"
    assert data["created_at"]
    assert data["processed_at"] is None
    assert data["failure_reason"] is None


async def test_get_payment_returns_404_for_missing_payment(client) -> None:
    """GET должен явно сообщать, что платеж не найден."""

    response = await client.get(
        "/api/v1/payments/00000000-0000-0000-0000-000000000001",
        headers={"X-API-Key": "test-api-key"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_get_payment_requires_api_key(client) -> None:
    """Отсутствующий API key должен приводить к контролируемому отказу авторизации."""

    response = await client.get("/api/v1/payments/00000000-0000-0000-0000-000000000001")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid API key"}


async def test_get_payment_rejects_invalid_api_key(client) -> None:
    """Неверный API key должен приводить к тому же отказу, что и отсутствующий."""

    response = await client.get(
        "/api/v1/payments/00000000-0000-0000-0000-000000000001",
        headers={"X-API-Key": "wrong-key"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid API key"}
