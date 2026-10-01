"""Test fixtures: minimal Home Assistant stubs.

The real homeassistant package is heavy and not needed for the logic
under test. If it IS installed (for example inside a Home Assistant dev
environment) the real package is used and no stubs are injected.
"""

import sys
import types
from datetime import datetime

try:
    import homeassistant  # noqa: F401
except Exception:  # noqa: BLE001 - stub path is the expected one
    _STUB = True
else:
    _STUB = False

import pytest  # noqa: E402

if _STUB:

    def _module(name: str) -> types.ModuleType:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
        return mod

    # --- homeassistant (package marker) -------------------------------------
    ha = _module("homeassistant")
    ha.__path__ = []  # type: ignore[attr-defined]

    # --- homeassistant.core --------------------------------------------------
    core = _module("homeassistant.core")
    core.HomeAssistant = type("HomeAssistant", (), {})
    core.callback = lambda fn: fn
    ha.core = core

    # --- homeassistant.data_entry_flow ---------------------------------------
    flow_mod = _module("homeassistant.data_entry_flow")
    flow_mod.FlowResult = dict
    ha.data_entry_flow = flow_mod

    # --- homeassistant.exceptions --------------------------------------------
    exc = _module("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        """Stub base for HA errors."""

    class ConfigEntryAuthFailed(HomeAssistantError):
        """Stub: raised when credentials must be re-entered."""

    exc.HomeAssistantError = HomeAssistantError
    exc.ConfigEntryAuthFailed = ConfigEntryAuthFailed
    ha.exceptions = exc

    # --- homeassistant.config_entries ----------------------------------------
    ce = _module("homeassistant.config_entries")
    ce.ConfigEntry = type("ConfigEntry", (), {})

    class _AbortFlow(Exception):
        """Stub stand-in for data_entry_flow.AbortFlow."""

    class _FlowBase:
        """Shared no-op flow plumbing for the stub ConfigFlow/OptionsFlow."""

        def async_show_form(
            self, step_id, data_schema=None, errors=None, description_placeholders=None
        ):
            return {
                "type": "form",
                "step_id": step_id,
                "errors": errors or {},
                "description_placeholders": description_placeholders or {},
            }

        def async_create_entry(self, title=None, data=None):
            return {"type": "create_entry", "title": title or "", "data": data or {}}

        def async_abort(self, reason):
            return {"type": "abort", "reason": reason}

        def async_update_reload_and_abort(self, entry, data_updates=None):
            return {
                "type": "abort",
                "reason": "reauth_successful",
                "data_updates": data_updates,
            }

        def async_set_unique_id(self, unique_id):
            """Real HA's ConfigFlow.async_set_unique_id is a coroutine."""
            self._unique_id = unique_id
            return _CompletedStub()

        def _abort_if_unique_id_configured(self, updates=None, error=None):
            existing = getattr(self, "_existing_unique_ids", set())
            if getattr(self, "_unique_id", None) in existing:
                raise _AbortFlow(self._unique_id)

        def _get_reauth_entry(self):  # pragma: no cover - tests assign their own
            return None


class _CompletedStub:
    """Awaitable that resolves immediately, mimicking HA's coroutine returns."""

    def __await__(self):
        async def _noop():
            return None

        return _noop().__await__()

    class ConfigFlow(_FlowBase):
        """Stub ConfigFlow accepting the domain= keyword."""

        def __init_subclass__(cls, domain=None, **kwargs):
            super().__init_subclass__(**kwargs)

    class OptionsFlow(_FlowBase):
        """Stub OptionsFlow."""

        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)

    ce.ConfigFlow = ConfigFlow
    ce.OptionsFlow = OptionsFlow
    ce.AbortFlow = _AbortFlow
    ha.config_entries = ce

    # --- homeassistant.const -------------------------------------------------
    const = _module("homeassistant.const")

    class Platform:
        """Stub HA platform enum."""

        BINARY_SENSOR = "binary_sensor"
        SENSOR = "sensor"

    const.Platform = Platform
    ha.const = const

    # --- homeassistant.helpers.* ---------------------------------------------
    helpers = _module("homeassistant.helpers")
    ha.helpers = helpers

    uc = _module("homeassistant.helpers.update_coordinator")

    class DataUpdateCoordinator:
        """Stub with the constructor signature used by the integration."""

        def __init__(self, hass, logger, name=None, update_interval=None, **kwargs):
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval
            self.data = None

    class UpdateFailed(HomeAssistantError):
        """Stub: raised when a data refresh fails."""

    uc.DataUpdateCoordinator = DataUpdateCoordinator
    uc.UpdateFailed = UpdateFailed
    helpers.update_coordinator = uc

    ac = _module("homeassistant.helpers.aiohttp_client")
    ac.async_get_clientsession = lambda hass, verify_ssl=True: None
    helpers.aiohttp_client = ac

    # --- homeassistant.util.dt -----------------------------------------------
    util = _module("homeassistant.util")
    ha.util = util

    dt = _module("homeassistant.util.dt")

    def _parse_datetime(value):
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    dt.parse_datetime = _parse_datetime
    dt.now = lambda: datetime.now().astimezone()
    util.dt = dt

    # homeassistant.util.dt must also exist as an attribute on ha.util AND the
    # real integration does `from homeassistant.util.dt import now` - covered.