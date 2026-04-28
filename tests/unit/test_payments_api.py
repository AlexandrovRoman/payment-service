"""Unit tests for the payment creation API endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_payment_returns_202(client: AsyncClient, payment_payload: dict) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=payment_payload,
        headers={"Idempotency-Key": "key-001"},
    )
    assert response.status_code == 202
    data = response.json()
    assert "payment_id" in data
    assert data["status"] == "pending"
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_payment_idempotency(client: AsyncClient, payment_payload: dict) -> None:
    """Same idempotency key should return the same payment."""
    r1 = await client.post(
        "/api/v1/payments",
        json=payment_payload,
        headers={"Idempotency-Key": "key-idem"},
    )
    r2 = await client.post(
        "/api/v1/payments",
        json=payment_payload,
        headers={"Idempotency-Key": "key-idem"},
    )
    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r1.json()["payment_id"] == r2.json()["payment_id"]


@pytest.mark.asyncio
async def test_get_payment_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/payments/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_payment_returns_details(client: AsyncClient, payment_payload: dict) -> None:
    create_resp = await client.post(
        "/api/v1/payments",
        json=payment_payload,
        headers={"Idempotency-Key": "key-get-test"},
    )
    payment_id = create_resp.json()["payment_id"]

    get_resp = await client.get(f"/api/v1/payments/{payment_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["payment_id"] == payment_id
    assert data["status"] == "pending"
    assert data["currency"] == "RUB"


@pytest.mark.asyncio
async def test_missing_api_key_returns_403(payment_payload: dict) -> None:
    """Requests without X-API-Key should be rejected."""
    from httpx import ASGITransport, AsyncClient

    from payment_service.main import create_app

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/payments",
            json=payment_payload,
            headers={"Idempotency-Key": "key-noauth"},
        )
    assert resp.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_missing_idempotency_key_returns_422(
    client: AsyncClient, payment_payload: dict
) -> None:
    """Requests without Idempotency-Key header should fail validation."""
    resp = await client.post("/api/v1/payments", json=payment_payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_currency_returns_422(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/payments",
        json={"amount": "50.00", "currency": "INVALID"},
        headers={"Idempotency-Key": "key-bad-currency"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_negative_amount_returns_422(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/payments",
        json={"amount": "-10.00", "currency": "USD"},
        headers={"Idempotency-Key": "key-negative"},
    )
    assert resp.status_code == 422
