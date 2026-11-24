"""Tests for Napper service payloads."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.napper import services


@pytest.mark.parametrize(
    ("diaper_content", "expected"),
    [("DIRTY", "DIRTY"), ("POOP", "DIRTY"), ("WET", "WET"), ("MIXED", "MIXED")],
)
@pytest.mark.asyncio
async def test_diaper_change_payload(monkeypatch, diaper_content, expected):
    """Send canonical content for both current and legacy dirty inputs."""
    hass = SimpleNamespace(services=SimpleNamespace(async_register=Mock()))
    coordinator = SimpleNamespace(
        entry=SimpleNamespace(data={}), baby_id="baby-1", async_request_refresh=AsyncMock()
    )
    request = AsyncMock(return_value={})
    monkeypatch.setattr(services, "_make_api_request", request)
    await services.async_register_services(hass, coordinator)
    registration = next(
        call for call in hass.services.async_register.call_args_list
        if call.args[1] == "log_diaper_change"
    )
    handler = registration.args[2]
    data = registration.kwargs["schema"]({"diaper_content": diaper_content})
    await handler(SimpleNamespace(data=data))
    assert request.await_args.args[4]["diaperContent"] == expected
