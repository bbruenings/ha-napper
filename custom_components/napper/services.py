"""Services for Napper integration."""

import logging
import uuid
from datetime import datetime
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    API_BASE_URL,
    CONF_BABY_ID,
    CONF_ID_TOKEN,
    CONF_USER_ID,
    LOG_CATEGORY_NAP,
    LOG_CATEGORY_CHANGED_DIAPER,
    LOG_CATEGORY_SOLIDS,
    LOG_CATEGORY_BED_TIME,
    LOG_CATEGORY_WOKE_UP,
    LOG_CATEGORY_NURSING,
    LOG_CATEGORY_NIGHT_WAKING,
    LOG_CATEGORY_TEMPERATURE,
    LOG_CATEGORY_MEDICINE,
    DIAPER_WET,
    DIAPER_MIXED,
    DIAPER_POOP,
)
from .coordinator import NapperDataUpdateCoordinator
from .api import parse_json_response

_LOGGER = logging.getLogger(__name__)
SERVICE_NAMES = [
    "log_diaper_change",
    "log_solids",
    "log_solid_food",
    "log_sleep_start",
    "log_sleep_end",
    "log_wake_up",
    "log_bedtime",
    "log_nursing",
    "delete_log",
    "get_logs",
]

# Service schemas
LOG_DIAPER_CHANGE_SCHEMA = vol.Schema({
    vol.Required("diaper_content"): vol.In([DIAPER_WET, DIAPER_MIXED, DIAPER_POOP]),
    vol.Optional("comment", default=""): str,
    vol.Optional("timestamp"): str,
})

LOG_SOLIDS_SCHEMA = vol.Schema({
    vol.Optional("comment", default=""): str,
    vol.Optional("timestamp"): str,
})

LOG_SLEEP_START_SCHEMA = vol.Schema({
    vol.Optional("comment", default=""): str,
    vol.Optional("timestamp"): str,
})

LOG_SLEEP_END_SCHEMA = vol.Schema({
    vol.Optional("log_id"): str,
    vol.Optional("comment", default=""): str,
    vol.Optional("timestamp"): str,
})

LOG_WAKE_UP_SCHEMA = vol.Schema({
    vol.Optional("comment", default=""): str,
    vol.Optional("timestamp"): str,
})

LOG_BEDTIME_SCHEMA = vol.Schema({
    vol.Optional("comment", default=""): str,
    vol.Optional("timestamp"): str,
})

LOG_NURSING_SCHEMA = vol.Schema({
    vol.Optional("comment", default=""): str,
    vol.Optional("timestamp"): str,
})

DELETE_LOG_SCHEMA = vol.Schema({
    vol.Required("log_id"): str,
})

GET_LOGS_SCHEMA = vol.Schema({
    vol.Optional("category"): str,
})


def _get_current_timestamp(timestamp_str: str | None) -> str:
    """Get current timestamp or use provided one."""
    if timestamp_str:
        return timestamp_str
    
    now = datetime.now().astimezone()
    return now.isoformat(timespec='milliseconds')


def _generate_log_id(category: str) -> str:
    """Generate a unique log ID."""
    unique_id = str(uuid.uuid4())
    return f"LOG_{unique_id}_{category}"


async def _make_api_request(
    hass: HomeAssistant,
    coordinator: NapperDataUpdateCoordinator,
    method: str,
    endpoint: str,
    data: dict | None = None,
) -> dict:
    """Make an API request to Napper."""
    session = aiohttp.ClientSession()
    try:
        url = f"{API_BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {coordinator._token}",
            "Content-Type": "application/json",
        }
        
        _LOGGER.debug("Making %s request to %s", method, url)
        
        if method == "GET":
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                return await parse_json_response(response)
        elif method == "PUT":
            async with session.put(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                return await parse_json_response(response)
        elif method == "DELETE":
            async with session.delete(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                return await parse_json_response(response)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
            
    except aiohttp.ClientError as err:
        _LOGGER.error("API request failed: %s", err)
        raise HomeAssistantError(f"API request failed: {err}")
    finally:
        await session.close()


async def async_register_services(hass: HomeAssistant, coordinator: NapperDataUpdateCoordinator) -> None:
    """Register Napper services."""
    
    async def log_diaper_change(call: ServiceCall) -> ServiceResponse:
        """Log a diaper change."""
        diaper_content = call.data.get("diaper_content", DIAPER_WET)
        comment = call.data.get("comment", "")
        timestamp = _get_current_timestamp(call.data.get("timestamp"))
        
        user_id = coordinator.entry.data.get(CONF_USER_ID, "")
        log_id = _generate_log_id(LOG_CATEGORY_CHANGED_DIAPER)
        
        payload = {
            "id": log_id,
            "start": timestamp,
            "end": timestamp,
            "category": LOG_CATEGORY_CHANGED_DIAPER,
            "diaperContent": diaper_content,
            "comment": comment,
            "isOpen": False,
            "createdByUserId": user_id,
            "skipped": False,
        }
        
        result = await _make_api_request(
            hass, coordinator, "PUT", f"/logs/{coordinator.baby_id}", payload
        )
        
        # Force a refresh of the coordinator
        await coordinator.async_request_refresh()
        
        return {"log_id": log_id, "success": True}
    
    async def log_solids(call: ServiceCall) -> ServiceResponse:
        """Log solid food feeding."""
        comment = call.data.get("comment", "")
        timestamp = _get_current_timestamp(call.data.get("timestamp"))
        
        user_id = coordinator.entry.data.get(CONF_USER_ID, "")
        log_id = _generate_log_id(LOG_CATEGORY_SOLIDS)
        
        payload = {
            "id": log_id,
            "start": timestamp,
            "end": timestamp,
            "category": LOG_CATEGORY_SOLIDS,
            "comment": comment,
            "isOpen": False,
            "createdByUserId": user_id,
            "skipped": False,
        }
        
        result = await _make_api_request(
            hass, coordinator, "PUT", f"/logs/{coordinator.baby_id}", payload
        )
        
        await coordinator.async_request_refresh()
        
        return {"log_id": log_id, "success": True}
    
    async def log_sleep_start(call: ServiceCall) -> ServiceResponse:
        """Log sleep/nap start."""
        comment = call.data.get("comment", "")
        timestamp = _get_current_timestamp(call.data.get("timestamp"))
        
        user_id = coordinator.entry.data.get(CONF_USER_ID, "")
        log_id = _generate_log_id(LOG_CATEGORY_NAP)
        
        payload = {
            "id": log_id,
            "start": timestamp,
            "end": timestamp,
            "category": LOG_CATEGORY_NAP,
            "comment": comment,
            "isOpen": True,  # Sleep is ongoing
            "createdByUserId": user_id,
            "skipped": False,
        }
        
        result = await _make_api_request(
            hass, coordinator, "PUT", f"/logs/{coordinator.baby_id}", payload
        )
        
        await coordinator.async_request_refresh()
        
        return {"log_id": log_id, "success": True}
    
    async def log_sleep_end(call: ServiceCall) -> ServiceResponse:
        """Log sleep/nap end by updating existing nap log."""
        log_id = call.data.get("log_id")
        comment = call.data.get("comment", "")
        timestamp = _get_current_timestamp(call.data.get("timestamp"))
        
        user_id = coordinator.entry.data.get(CONF_USER_ID, "")
        
        # If log_id is provided, update the existing nap log to close it
        if log_id:
            # Fetch the existing nap log to update it
            try:
                # Get current logs to find the nap
                if not coordinator.data:
                    await coordinator.async_request_refresh()
                
                all_logs = coordinator.data.get("all_logs", []) if coordinator.data else []
                
                # Find the open nap log
                nap_log = None
                if log_id == "current":
                    # Find the currently open nap
                    for log in all_logs:
                        if log.get("category") == LOG_CATEGORY_NAP and log.get("isOpen", False):
                            nap_log = log
                            break
                else:
                    # Use the provided log_id
                    for log in all_logs:
                        if log.get("id") == log_id:
                            nap_log = log
                            break
                
                if nap_log:
                    # Update the existing nap log to close it
                    payload = {
                        **nap_log,
                        "end": timestamp,
                        "isOpen": False,
                        "comment": nap_log.get("comment", "") + (" - " + comment if comment else ""),
                    }
                    
                    result = await _make_api_request(
                        hass, coordinator, "PUT", f"/logs/{coordinator.baby_id}", payload
                    )
                    
                    await coordinator.async_request_refresh()
                    
                    return {"log_id": nap_log.get("id"), "success": True, "action": "closed_nap"}
                else:
                    _LOGGER.warning("No open nap log found with id %s", log_id)
                    # Fall through to create WOKE_UP entry
            except Exception as err:
                _LOGGER.error("Error closing nap log: %s", err)
                # Fall through to create WOKE_UP entry
        
        # If no log_id or failed to find nap, create a WOKE_UP entry
        woke_up_id = _generate_log_id(LOG_CATEGORY_WOKE_UP)
        
        payload = {
            "id": woke_up_id,
            "start": timestamp,
            "end": timestamp,
            "category": LOG_CATEGORY_WOKE_UP,
            "comment": comment,
            "isOpen": False,
            "createdByUserId": user_id,
            "skipped": False,
        }
        
        result = await _make_api_request(
            hass, coordinator, "PUT", f"/logs/{coordinator.baby_id}", payload
        )
        
        await coordinator.async_request_refresh()
        
        return {"log_id": woke_up_id, "success": True, "action": "created_wake_up"}
    
    async def log_wake_up(call: ServiceCall) -> ServiceResponse:
        """Log wake up event."""
        comment = call.data.get("comment", "")
        timestamp = _get_current_timestamp(call.data.get("timestamp"))
        
        user_id = coordinator.entry.data.get(CONF_USER_ID, "")
        log_id = _generate_log_id(LOG_CATEGORY_WOKE_UP)
        
        payload = {
            "id": log_id,
            "start": timestamp,
            "end": timestamp,
            "category": LOG_CATEGORY_WOKE_UP,
            "comment": comment,
            "isOpen": False,
            "createdByUserId": user_id,
            "skipped": False,
        }
        
        result = await _make_api_request(
            hass, coordinator, "PUT", f"/logs/{coordinator.baby_id}", payload
        )
        
        await coordinator.async_request_refresh()
        
        return {"log_id": log_id, "success": True}
    
    async def log_bedtime(call: ServiceCall) -> ServiceResponse:
        """Log bedtime."""
        comment = call.data.get("comment", "")
        timestamp = _get_current_timestamp(call.data.get("timestamp"))
        
        user_id = coordinator.entry.data.get(CONF_USER_ID, "")
        log_id = _generate_log_id(LOG_CATEGORY_BED_TIME)
        
        payload = {
            "id": log_id,
            "start": timestamp,
            "end": timestamp,
            "category": LOG_CATEGORY_BED_TIME,
            "comment": comment,
            "isOpen": False,
            "createdByUserId": user_id,
            "skipped": False,
        }
        
        result = await _make_api_request(
            hass, coordinator, "PUT", f"/logs/{coordinator.baby_id}", payload
        )
        
        await coordinator.async_request_refresh()
        
        return {"log_id": log_id, "success": True}
    
    async def log_nursing(call: ServiceCall) -> ServiceResponse:
        """Log nursing session."""
        comment = call.data.get("comment", "")
        timestamp = _get_current_timestamp(call.data.get("timestamp"))
        
        user_id = coordinator.entry.data.get(CONF_USER_ID, "")
        log_id = _generate_log_id(LOG_CATEGORY_NURSING)
        
        payload = {
            "id": log_id,
            "start": timestamp,
            "end": timestamp,
            "category": LOG_CATEGORY_NURSING,
            "comment": comment,
            "isOpen": False,
            "createdByUserId": user_id,
            "skipped": False,
        }
        
        result = await _make_api_request(
            hass, coordinator, "PUT", f"/logs/{coordinator.baby_id}", payload
        )
        
        await coordinator.async_request_refresh()
        
        return {"log_id": log_id, "success": True}
    
    async def delete_log(call: ServiceCall) -> ServiceResponse:
        """Delete a log entry."""
        log_id = call.data.get("log_id")
        
        result = await _make_api_request(
            hass, coordinator, "DELETE", f"/logs/{coordinator.baby_id}/{log_id}"
        )
        
        await coordinator.async_request_refresh()
        
        return {"success": True}
    
    async def get_logs(call: ServiceCall) -> ServiceResponse:
        """Get all logs, optionally filtered by category."""
        category = call.data.get("category")
        
        if not coordinator.data:
            await coordinator.async_request_refresh()
        
        all_logs = coordinator.data.get("all_logs", []) if coordinator.data else []
        
        if category:
            filtered_logs = [log for log in all_logs if log.get("category") == category]
        else:
            filtered_logs = all_logs
        
        return {"logs": filtered_logs, "count": len(filtered_logs)}
    
    # Register services
    hass.services.async_register(
        DOMAIN,
        "log_diaper_change",
        log_diaper_change,
        schema=LOG_DIAPER_CHANGE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    
    hass.services.async_register(
        DOMAIN,
        "log_solids",
        log_solids,
        schema=LOG_SOLIDS_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    
    # Alias for log_solids
    hass.services.async_register(
        DOMAIN,
        "log_solid_food",
        log_solids,
        schema=LOG_SOLIDS_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    
    hass.services.async_register(
        DOMAIN,
        "log_sleep_start",
        log_sleep_start,
        schema=LOG_SLEEP_START_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    
    hass.services.async_register(
        DOMAIN,
        "log_sleep_end",
        log_sleep_end,
        schema=LOG_SLEEP_END_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    
    hass.services.async_register(
        DOMAIN,
        "log_wake_up",
        log_wake_up,
        schema=LOG_WAKE_UP_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    
    hass.services.async_register(
        DOMAIN,
        "log_bedtime",
        log_bedtime,
        schema=LOG_BEDTIME_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    
    hass.services.async_register(
        DOMAIN,
        "log_nursing",
        log_nursing,
        schema=LOG_NURSING_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    
    hass.services.async_register(
        DOMAIN,
        "delete_log",
        delete_log,
        schema=DELETE_LOG_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    
    hass.services.async_register(
        DOMAIN,
        "get_logs",
        get_logs,
        schema=GET_LOGS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


async def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister Napper services."""
    for service_name in SERVICE_NAMES:
        if hass.services.has_service(DOMAIN, service_name):
            hass.services.async_remove(DOMAIN, service_name)
            _LOGGER.debug("Unregistered service: %s.%s", DOMAIN, service_name)
