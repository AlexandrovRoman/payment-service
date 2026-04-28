"""Unit tests for the payment gateway emulator."""

import pytest

from payment_service.services.gateway import GatewayResult, process_payment


@pytest.mark.asyncio
async def test_gateway_returns_result() -> None:
    result = await process_payment(payment_id="test-id", amount="100.00", currency="RUB")
    assert isinstance(result, GatewayResult)
    assert isinstance(result.success, bool)
    assert result.message in ("approved", "declined_by_gateway")


@pytest.mark.asyncio
async def test_gateway_success_rate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force 100% success rate and verify result."""
    import payment_service.services.gateway as gw_module

    monkeypatch.setattr(gw_module.settings, "gateway_success_rate", 1.0)
    monkeypatch.setattr(gw_module.settings, "gateway_min_delay", 0.0)
    monkeypatch.setattr(gw_module.settings, "gateway_max_delay", 0.0)

    result = await process_payment("p1", "50.00", "USD")
    assert result.success is True


@pytest.mark.asyncio
async def test_gateway_failure_rate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force 0% success rate and verify failure result."""
    import payment_service.services.gateway as gw_module

    monkeypatch.setattr(gw_module.settings, "gateway_success_rate", 0.0)
    monkeypatch.setattr(gw_module.settings, "gateway_min_delay", 0.0)
    monkeypatch.setattr(gw_module.settings, "gateway_max_delay", 0.0)

    result = await process_payment("p2", "50.00", "EUR")
    assert result.success is False
