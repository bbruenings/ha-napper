"""Tests for the Napper shared API helpers (no Home Assistant required)."""

import json

import aiohttp
import pytest

from custom_components.napper.api import parse_json_response


class FakeResponse:
    """Minimal aiohttp response stand-in."""

    def __init__(self, text: str) -> None:
        self._text = text

    async def text(self) -> str:
        return self._text


@pytest.mark.asyncio
async def test_parse_json_response_parses_text_plain_json():
    """The API sends JSON with Content-Type text/plain - parse it anyway."""
    response = FakeResponse(json.dumps({"item": {"logs": []}}))
    assert await parse_json_response(response) == {"item": {"logs": []}}


@pytest.mark.asyncio
async def test_parse_json_response_empty_returns_none():
    """send-otp returns an empty body on success."""
    assert await parse_json_response(FakeResponse("")) is None
    assert await parse_json_response(FakeResponse("   ")) is None


@pytest.mark.asyncio
async def test_parse_json_response_non_object_returns_none():
    """The API sometimes returns a bare string literal."""
    assert await parse_json_response(FakeResponse('""')) is None
    assert await parse_json_response(FakeResponse("[1, 2]")) is None


@pytest.mark.asyncio
async def test_parse_json_response_invalid_json_raises_client_error():
    """Invalid JSON surfaces as aiohttp.ClientError."""
    with pytest.raises(aiohttp.ClientError):
        await parse_json_response(FakeResponse("not json"))


@pytest.mark.asyncio
async def test_parse_json_response_body_read_once():
    """Regression: the body must be read once, not twice (stream)."""
    calls = {"n": 0}

    class OnceResponse(FakeResponse):
        async def text(self):
            calls["n"] += 1
            return await super().text()

    await parse_json_response(OnceResponse('{"a": 1}'))
    assert calls["n"] == 1