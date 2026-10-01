"""Config flow for Napper integration."""

import asyncio
import json
import logging
import re
import uuid
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    API_BASE_URL,
    AUTH_SEND_OTP,
    AUTH_EMAIL_LOGIN,
    ENDPOINT_BABIES,
    CONF_EMAIL,
    CONF_OTP,
    CONF_BABY_ID,
    CONF_BABY_NAME,
    CONF_USER_ID,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRY,
    CONF_DEVICE_ID,
    FLOW_STATE_EMAIL,
    FLOW_STATE_OTP,
    FLOW_STATE_BABY,
)
from .api import parse_json_response

_LOGGER = logging.getLogger(__name__)


# Email validation regex (relaxed)
EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


async def send_otp(hass: HomeAssistant, email: str, device_id: str) -> dict:
    """Send OTP to email address."""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_BASE_URL}{AUTH_SEND_OTP}"
            
            payload = {
                "email": email,
                "useDeviceId": True,
                "source": "APP",
                "language": "en",
            }
            
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "napper/260819.092737 CFNetwork/3892.100.1 Darwin/27.0.0",
                "device": device_id,
                "source": "APP",
                "locale": "en-US",
                "language": "en",
            }
            
            _LOGGER.debug("Sending OTP with device ID: %s", device_id)
            _LOGGER.debug("Send OTP payload: %s", payload)
            
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                response_text = await response.text()
                _LOGGER.debug("Send OTP response status: %d", response.status)
                _LOGGER.debug("Send OTP response body: %s", response_text or "(empty)")
                
                if response.status == 400:
                    # Check if it's really an invalid email or something else
                    try:
                        error_data = json.loads(response_text) if response_text else {}
                        _LOGGER.debug("400 error details: %s", error_data)
                    except:
                        pass
                    return {"error": "invalid_email"}
                elif response.status != 200:
                    _LOGGER.error("Send OTP failed with status %d - body: %s", response.status, response_text)
                    return {"error": "connection_error"}
                
                # Success - empty response expected (returns "" or empty body)
                # Napper API returns text/plain with empty string for success
                return {"success": True}
                
    except asyncio.TimeoutError:
        return {"error": "timeout"}
    except aiohttp.ClientError as err:
        _LOGGER.error("Error sending OTP: %s", err)
        return {"error": "connection_error"}
    except Exception as err:
        _LOGGER.error("Unexpected error sending OTP: %s", err)
        return {"error": "unknown"}


async def verify_otp(hass: HomeAssistant, email: str, otp: str, device_id: str) -> dict:
    """Verify OTP and get tokens."""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_BASE_URL}{AUTH_EMAIL_LOGIN}"
            
            payload = {
                "email": email,
                "otp": otp,
                "useDeviceId": True,
            }
            
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "napper/260819.092737 CFNetwork/3892.100.1 Darwin/27.0.0",
                "device": device_id,
                "source": "APP",
                "locale": "en-US",
                "language": "en",
            }
            
            _LOGGER.debug("Verifying OTP with device ID: %s", device_id)
            _LOGGER.debug(
                "Verify OTP payload: email=%s, otp=***, useDeviceId=%s",
                email,
                True,
            )
            
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                response_text = await response.text()
                _LOGGER.debug("Verify OTP response status: %d", response.status)
                _LOGGER.debug(
                    "Verify OTP response body received (%d bytes)", len(response_text)
                )
                
                if response.status == 400:
                    _LOGGER.error("OTP verification rejected with status 400")
                    return {"error": "invalid_otp"}
                elif response.status == 401:
                    _LOGGER.error("OTP verification rejected with status 401")
                    return {"error": "invalid_otp"}
                elif response.status != 200:
                    _LOGGER.error(
                        "OTP verification failed with status %d", response.status
                    )
                    return {"error": "connection_error"}
                
                # Parse response - handle text/plain content-type with JSON body
                # Napper API returns text/plain even for JSON responses
                data = None
                if not response_text or response_text.strip() == "":
                    _LOGGER.error("Empty response from email-login endpoint")
                    return {"error": "invalid_response"}
                
                try:
                    data = json.loads(response_text)
                except json.JSONDecodeError as err:
                    _LOGGER.error("Could not parse email-login response: %s", err)
                    return {"error": "invalid_response"}
                
                # Ensure data is a dict (not a string, list, or other type)
                # Napper API can return "" (empty string literal) which parses to Python str
                if not isinstance(data, dict):
                    _LOGGER.error("Response is not a JSON object: %s", type(data).__name__)
                    return {"error": "invalid_response"}
                
                item = data.get("item", {})
                
                id_token_data = item.get("idToken", {})
                refresh_token_data = item.get("refreshToken", {})
                
                id_token = id_token_data.get("token", "")
                refresh_token = refresh_token_data.get("token", "")
                
                # Extract expiry from JWT payload or use default
                id_token_payload = id_token_data.get("payload", {})
                token_expiry = id_token_payload.get("exp", 0)
                user_id = id_token_payload.get("sub", "")
                
                if not id_token:
                    _LOGGER.error("No idToken in response")
                    return {"error": "invalid_token"}
                
                return {
                    "success": True,
                    "id_token": id_token,
                    "refresh_token": refresh_token,
                    "token_expiry": token_expiry,
                    "user_id": user_id,
                }
                
    except asyncio.TimeoutError:
        return {"error": "timeout"}
    except aiohttp.ClientError as err:
        _LOGGER.error("Error verifying OTP: %s", err)
        return {"error": "connection_error"}
    except Exception as err:
        _LOGGER.error("Unexpected error verifying OTP: %s", err)
        return {"error": "unknown"}


async def fetch_babies(hass: HomeAssistant, token: str, device_id: str = None) -> dict:
    """Fetch list of babies from API."""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_BASE_URL}{ENDPOINT_BABIES}"
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            
            # Add device headers if provided (for consistency)
            if device_id:
                headers["User-Agent"] = "napper/260819.092737 CFNetwork/3892.100.1 Darwin/27.0.0"
                headers["device"] = device_id
                headers["source"] = "APP"
                headers["locale"] = "en-US"
                headers["language"] = "en"
            
            _LOGGER.debug("Fetching babies with headers: %s", {k: v if k != 'Authorization' else '***' for k, v in headers.items()})
            
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                response_text = await response.text()
                _LOGGER.debug("Fetch babies response status: %d", response.status)
                _LOGGER.debug("Fetch babies response body: %s", response_text)
                
                if response.status == 401:
                    return {"error": "invalid_token"}
                elif response.status != 200:
                    _LOGGER.error("Fetch babies failed with status %d - body: %s", response.status, response_text)
                    # If babies endpoint doesn't exist, try to get from widget-today
                    return {"error": "baby_not_found"}
                
                # Parse response - handle text/plain content-type with JSON body
                # Napper API returns text/plain even for JSON responses
                data = None
                if not response_text or response_text.strip() == "":
                    _LOGGER.error("Empty response from babies endpoint")
                    return {"error": "no_babies"}
                
                try:
                    data = json.loads(response_text)
                except json.JSONDecodeError as err:
                    _LOGGER.error("Could not parse babies response as JSON: %s (error: %s)", response_text[:200], err)
                    return {"error": "invalid_response"}
                
                # Ensure data is a dict (not a string, list, or other type)
                if not isinstance(data, dict):
                    _LOGGER.error("Babies response is not a JSON object: %s", type(data).__name__)
                    return {"error": "invalid_response"}
                
                # API returns "items" (plural) not "item"
                babies = data.get("items", data.get("item", []))
                
                if not babies:
                    _LOGGER.warning("No babies found in response")
                    return {"error": "no_babies"}
                
                return {
                    "success": True,
                    "babies": babies,
                }
                
    except asyncio.TimeoutError:
        return {"error": "timeout"}
    except aiohttp.ClientError as err:
        _LOGGER.error("Error fetching babies: %s", err)
        return {"error": "connection_error"}
    except Exception as err:
        _LOGGER.error("Unexpected error fetching babies: %s", err)
        return {"error": "unknown"}


class NapperConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Napper."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.email: str | None = None
        self.otp: str | None = None
        self.id_token: str | None = None
        self.refresh_token: str | None = None
        self.token_expiry: int | None = None
        self.user_id: str | None = None
        self.babies: list | None = None
        self.selected_baby_id: str | None = None
        self.selected_baby_name: str | None = None
        self.device_id: str | None = None  # Device ID must be consistent across OTP flow
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: Ask for email address."""
        errors = {}

        if user_input is not None:
            email = user_input.get(CONF_EMAIL, "").strip().lower()
            
            _LOGGER.debug("Email entered: %s", email)
            
            if not email:
                errors["base"] = "email_required"
            elif "@" not in email or "." not in email:
                errors["base"] = "invalid_email"
            else:
                # Check if already configured with this email
                await self.async_set_unique_id(email)
                self._abort_if_unique_id_configured()
                
                # Generate consistent device ID for this auth session
                self.device_id = str(uuid.uuid4()).upper()
                _LOGGER.debug("Generated device ID: %s", self.device_id)
                
                # Send OTP
                _LOGGER.debug("Sending OTP to: %s", email)
                result = await send_otp(self.hass, email, self.device_id)
                _LOGGER.debug("Send OTP result: %s", result)
                
                if result.get("success"):
                    self.email = email
                    return await self.async_step_otp()
                else:
                    error = result.get("error", "unknown")
                    if error == "invalid_email":
                        errors["base"] = "invalid_email"
                    elif error == "timeout":
                        errors["base"] = "timeout"
                    else:
                        errors["base"] = "connection_error"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_EMAIL): str,
            }),
            errors=errors,
        )

    async def async_step_otp(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2: Ask for OTP code."""
        errors = {}

        if user_input is not None:
            otp = user_input.get(CONF_OTP, "").strip()
            
            if not otp:
                errors["base"] = "otp_required"
            elif len(otp) < 4 or len(otp) > 8:
                errors["base"] = "invalid_otp"
            else:
                # Verify OTP with same device ID
                _LOGGER.debug("Verifying OTP for email: %s, OTP length: %d, device_id: %s", self.email, len(otp), self.device_id)
                result = await verify_otp(self.hass, self.email, otp, self.device_id)
                _LOGGER.debug(
                    "Verify OTP completed successfully: %s",
                    bool(result.get("success")),
                )
                
                if result.get("success"):
                    self.otp = otp
                    self.id_token = result["id_token"]
                    self.refresh_token = result["refresh_token"]
                    self.token_expiry = result["token_expiry"]
                    self.user_id = result["user_id"]

                    if self._reauth_entry is not None:
                        return self.async_update_reload_and_abort(
                            self._reauth_entry,
                            data_updates={
                                CONF_EMAIL: self.email,
                                CONF_ID_TOKEN: self.id_token,
                                CONF_REFRESH_TOKEN: self.refresh_token,
                                CONF_TOKEN_EXPIRY: self.token_expiry,
                                CONF_USER_ID: self.user_id,
                                CONF_DEVICE_ID: self.device_id,
                            },
                        )
                    
                    # Fetch babies list with device ID for consistency
                    babies_result = await fetch_babies(self.hass, self.id_token, self.device_id)
                    
                    if babies_result.get("success"):
                        self.babies = babies_result["babies"]
                        return await self.async_step_baby()
                    else:
                        error = babies_result.get("error", "unknown")
                        if error == "invalid_token":
                            errors["base"] = "invalid_token"
                        elif error == "no_babies":
                            return self.async_abort(reason="no_babies")
                        else:
                            errors["base"] = "connection_error"
                else:
                    error = result.get("error", "unknown")
                    if error == "invalid_otp":
                        errors["base"] = "invalid_otp"
                    elif error == "timeout":
                        errors["base"] = "timeout"
                    else:
                        errors["base"] = "connection_error"

        # Format email for display (partially masked)
        email_display = self.email if self.email else "your email"
        
        return self.async_show_form(
            step_id="otp",
            data_schema=vol.Schema({
                vol.Required(CONF_OTP): str,
            }),
            description_placeholders={"email": email_display},
            errors=errors,
        )

    async def async_step_baby(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3: Select baby to monitor."""
        errors = {}

        if user_input is not None:
            baby_id = user_input.get(CONF_BABY_ID, "")
            
            if not baby_id:
                errors["base"] = "baby_required"
            else:
                # Find baby name
                baby_name = "Baby"
                for baby in self.babies:
                    if baby.get("id") == baby_id:
                        baby_name = baby.get("name", "Baby")
                        break
                
                self.selected_baby_id = baby_id
                self.selected_baby_name = baby_name
                
                # Create config entry
                return self.async_create_entry(
                    title=f"Napper - {baby_name}",
                    data={
                        CONF_EMAIL: self.email,
                        CONF_ID_TOKEN: self.id_token,
                        CONF_REFRESH_TOKEN: self.refresh_token,
                        CONF_TOKEN_EXPIRY: self.token_expiry,
                        CONF_DEVICE_ID: self.device_id,
                        CONF_USER_ID: self.user_id,
                        CONF_BABY_ID: baby_id,
                        CONF_BABY_NAME: baby_name,
                    },
                )

        # Build baby selector
        baby_options = {}
        for baby in self.babies or []:
            baby_id = baby.get("id", "")
            baby_name = baby.get("name", "Baby")
            baby_options[baby_id] = baby_name

        return self.async_show_form(
            step_id="baby",
            data_schema=vol.Schema({
                vol.Required(CONF_BABY_ID): vol.In(baby_options),
            }),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Start reauthentication for an existing config entry."""
        self._reauth_entry = self._get_reauth_entry()
        self.email = entry_data.get(CONF_EMAIL)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm reauthentication and send a new OTP."""
        errors = {}

        if user_input is not None:
            if not self.email:
                return self.async_abort(reason="auth_failed")

            self.device_id = str(uuid.uuid4()).upper()
            result = await send_otp(self.hass, self.email, self.device_id)
            if result.get("success"):
                return await self.async_step_otp()

            error = result.get("error", "unknown")
            errors["base"] = (
                "timeout" if error == "timeout" else "connection_error"
            )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({}),
            description_placeholders={"email": self.email or "your email"},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return NapperOptionsFlow(config_entry)


class NapperOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Napper."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_BABY_NAME,
                    default=self.config_entry.data.get(CONF_BABY_NAME, "Baby"),
                ): str,
            }),
        )


class InvalidToken(HomeAssistantError):
    """Error to indicate invalid token."""


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
