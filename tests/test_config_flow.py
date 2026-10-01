"""Tests for the Napper config flow (stubbed homeassistant)."""

from types import SimpleNamespace

import pytest

from custom_components.napper.config_flow import NapperConfigFlow
from custom_components.napper.const import (
    CONF_BABY_ID,
    CONF_EMAIL,
    CONF_OTP,
)


def make_flow() -> NapperConfigFlow:
    """Build a config flow without running HA's ConfigFlow.__init__."""
    flow = object.__new__(NapperConfigFlow)
    flow.hass = SimpleNamespace()
    flow.email = None
    flow.otp = None
    flow.id_token = None
    flow.refresh_token = None
    flow.token_expiry = None
    flow.user_id = None
    flow.babies = None
    flow.selected_baby_id = None
    flow.selected_baby_name = None
    flow.device_id = None
    flow._reauth_entry = None
    return flow


@pytest.mark.asyncio
class TestEmailStep:
    async def test_blank_email_shows_error(self):
        flow = make_flow()
        result = await flow.async_step_user({CONF_EMAIL: "   "})
        assert result["type"] == "form"
        assert result["errors"] == {"base": "email_required"}

    async def test_malformed_email_shows_error(self):
        flow = make_flow()
        result = await flow.async_step_user({CONF_EMAIL: "not-an-email"})
        assert result["type"] == "form"
        assert result["errors"] == {"base": "invalid_email"}

    async def test_valid_email_generates_device_id_and_sends_otp(self, monkeypatch):
        flow = make_flow()
        sent = {}

        async def fake_send_otp(hass, email, device_id):
            sent["email"] = email
            sent["device_id"] = device_id
            return {"success": True}

        monkeypatch.setattr(
            "custom_components.napper.config_flow.send_otp", fake_send_otp
        )

        result = await flow.async_step_user({CONF_EMAIL: "Parent@Example.com "})

        # OTP step shown
        assert result["type"] == "form"
        assert result["step_id"] == "otp"
        # Email normalised, device id generated once and reused later
        assert flow.email == "parent@example.com"
        assert flow.device_id == sent["device_id"]
        assert len(flow.device_id) == 36  # UUID

    async def test_send_otp_failure_maps_to_connection_error(self, monkeypatch):
        flow = make_flow()

        async def fake_send_otp(hass, email, device_id):
            return {"error": "timeout"}

        monkeypatch.setattr(
            "custom_components.napper.config_flow.send_otp", fake_send_otp
        )
        result = await flow.async_step_user({CONF_EMAIL: "parent@example.com"})
        assert result["errors"] == {"base": "timeout"}


@pytest.mark.asyncio
class TestOtpStep:
    async def test_empty_otp_rejected(self):
        flow = make_flow()
        flow.email = "parent@example.com"
        result = await flow.async_step_otp({CONF_OTP: "  "})
        assert result["errors"] == {"base": "otp_required"}

    async def test_short_otp_rejected(self):
        flow = make_flow()
        flow.email = "parent@example.com"
        result = await flow.async_step_otp({CONF_OTP: "12"})
        assert result["errors"] == {"base": "invalid_otp"}

    async def test_invalid_otp_maps_error(self, monkeypatch):
        flow = make_flow()
        flow.email = "parent@example.com"
        flow.device_id = "DEVICE-ID"

        async def fake_verify(hass, email, otp, device_id):
            return {"error": "invalid_otp"}

        monkeypatch.setattr(
            "custom_components.napper.config_flow.verify_otp", fake_verify
        )
        result = await flow.async_step_otp({CONF_OTP: "123456"})
        assert result["errors"] == {"base": "invalid_otp"}

    async def test_valid_otp_with_babies_advances_to_baby_step(self, monkeypatch):
        flow = make_flow()
        flow.email = "parent@example.com"
        flow.device_id = "DEVICE-ID"

        async def fake_verify(hass, email, otp, device_id):
            return {
                "success": True,
                "id_token": "tok",
                "refresh_token": "ref",
                "token_expiry": 123,
                "user_id": "u1",
            }

        async def fake_fetch_babies(hass, token, device_id=None):
            return {"success": True, "babies": [{"id": "b1", "name": "Neo"}]}

        monkeypatch.setattr(
            "custom_components.napper.config_flow.verify_otp", fake_verify
        )
        monkeypatch.setattr(
            "custom_components.napper.config_flow.fetch_babies", fake_fetch_babies
        )

        result = await flow.async_step_otp({CONF_OTP: "123456"})
        assert result["type"] == "form"
        assert result["step_id"] == "baby"
        assert flow.id_token == "tok"
        assert flow.babies == [{"id": "b1", "name": "Neo"}]

    async def test_valid_otp_with_no_babies_aborts(self, monkeypatch):
        flow = make_flow()
        flow.email = "parent@example.com"
        flow.device_id = "DEVICE-ID"

        async def fake_verify(hass, email, otp, device_id):
            return {
                "success": True,
                "id_token": "tok",
                "refresh_token": "ref",
                "token_expiry": 123,
                "user_id": "u1",
            }

        async def fake_fetch_babies(hass, token, device_id=None):
            return {"error": "no_babies"}

        monkeypatch.setattr(
            "custom_components.napper.config_flow.verify_otp", fake_verify
        )
        monkeypatch.setattr(
            "custom_components.napper.config_flow.fetch_babies", fake_fetch_babies
        )

        result = await flow.async_step_otp({CONF_OTP: "123456"})
        assert result == {"type": "abort", "reason": "no_babies"}


@pytest.mark.asyncio
class TestBabyStep:
    async def test_missing_babies_list_defaults_to_empty_options(self):
        flow = make_flow()
        result = await flow.async_step_baby(None)
        assert result["type"] == "form"
        assert result["step_id"] == "baby"

    async def test_selection_creates_entry_with_all_data(self, monkeypatch):
        flow = make_flow()
        flow.email = "parent@example.com"
        flow.id_token = "tok"
        flow.refresh_token = "ref"
        flow.token_expiry = 123
        flow.user_id = "u1"
        flow.device_id = "DEVICE-ID"
        flow.babies = [{"id": "b1", "name": "Neo"}, {"id": "b2", "name": "Rook"}]

        result = await flow.async_step_baby({CONF_BABY_ID: "b2"})
        assert result["type"] == "create_entry"
        assert result["title"] == "Napper - Rook"
        data = result["data"]
        assert data[CONF_BABY_ID] == "b2"
        assert data[CONF_EMAIL] == "parent@example.com"
        assert data["device_id"] == "DEVICE-ID"


@pytest.mark.asyncio
class TestReauthStep:
    async def test_missing_email_aborts(self):
        flow = make_flow()
        flow.email = None
        result = await flow.async_step_reauth_confirm({CONF_EMAIL: True})
        assert result == {"type": "abort", "reason": "auth_failed"}

    async def test_reauth_confirm_sends_otp_and_advances(self, monkeypatch):
        flow = make_flow()
        flow._reauth_entry = SimpleNamespace(data={CONF_EMAIL: "parent@example.com"})
        flow.email = "parent@example.com"
        sent = {}

        async def fake_send_otp(hass, email, device_id):
            sent["device_id"] = device_id
            return {"success": True}

        monkeypatch.setattr(
            "custom_components.napper.config_flow.send_otp", fake_send_otp
        )
        # Step 1: no user input -> show the confirm form first
        result = await flow.async_step_reauth_confirm(None)
        assert result["type"] == "form"
        assert result["step_id"] == "reauth_confirm"

        # Step 2: user confirms -> OTP sent, otp step shown
        result = await flow.async_step_reauth_confirm({})
        assert result["type"] == "form"
        assert result["step_id"] == "otp"
        # Reauth generates a fresh device ID for the new OTP session
        assert sent["device_id"] == flow.device_id
        assert flow.device_id is not None

    async def test_reauth_otp_success_updates_entry_and_aborts(self, monkeypatch):
        flow = make_flow()
        entry = SimpleNamespace(data={CONF_EMAIL: "parent@example.com"})
        flow._reauth_entry = entry
        flow.email = "parent@example.com"
        flow.device_id = "DEVICE-ID"

        async def fake_verify(hass, email, otp, device_id):
            return {
                "success": True,
                "id_token": "newtok",
                "refresh_token": "newref",
                "token_expiry": 999,
                "user_id": "u1",
            }

        monkeypatch.setattr(
            "custom_components.napper.config_flow.verify_otp", fake_verify
        )
        result = await flow.async_step_otp({CONF_OTP: "123456"})
        assert result["type"] == "abort"
        assert result["reason"] == "reauth_successful"
        assert result["data_updates"]["id_token"] == "newtok"
        assert result["data_updates"]["device_id"] == "DEVICE-ID"