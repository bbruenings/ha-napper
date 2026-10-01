"""Data update coordinator for Napper API."""

import asyncio
from datetime import datetime, timedelta
import json
import logging

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.dt import parse_datetime

from .const import (
    API_BASE_URL,
    ENDPOINT_WIDGET_TODAY,
    AUTH_REFRESH_TOKEN,
    DOMAIN,
    CONF_BABY_ID,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRY,
    CONF_DEVICE_ID,
)
from .api import parse_json_response

_LOGGER = logging.getLogger(__name__)

# Refresh token 5 days before expiry
TOKEN_REFRESH_BUFFER = 5 * 24 * 60 * 60  # 5 days in seconds
DEFAULT_TOKEN_LIFETIME = 30 * 24 * 60 * 60


def is_permanent_refresh_error(status: int, data: dict | None) -> bool:
    """Return whether a refresh response means the credentials are unusable."""
    if status in (401, 403):
        return True
    if status != 400:
        return False

    message = str((data or {}).get("message", "")).lower()
    return "refresh token" in message or "token-mismatch" in message


class NapperDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to manage data updates from Napper API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self.baby_id = entry.data.get(CONF_BABY_ID)
        self._token = entry.data.get(CONF_ID_TOKEN)
        self._refresh_token = entry.data.get(CONF_REFRESH_TOKEN)
        self._token_expiry = entry.data.get(CONF_TOKEN_EXPIRY, 0)
        self._device_id = entry.data.get(CONF_DEVICE_ID)
        self._refresh_lock = asyncio.Lock()
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )

    def _is_token_expired(self) -> bool:
        """Check if token is expired or about to expire."""
        if not self._token_expiry:
            return True

        try:
            token_expiry = float(self._token_expiry)
        except (TypeError, ValueError):
            return True

        # Check if token expires within refresh buffer
        now = datetime.now().timestamp()
        return (token_expiry - now) < TOKEN_REFRESH_BUFFER

    async def _refresh_token_if_needed(self, *, force: bool = False) -> None:
        """Refresh an expiring or rejected token."""
        if not force and not self._is_token_expired():
            return

        token_before_lock = self._token

        async with self._refresh_lock:
            # Another caller may have refreshed while this caller waited.
            if force and self._token != token_before_lock:
                return
            if not force and not self._is_token_expired():
                return

            if not self._refresh_token:
                raise ConfigEntryAuthFailed("No refresh token available")
            if not self._device_id:
                raise ConfigEntryAuthFailed(
                    "Device identity is missing; reauthentication is required"
                )

            try:
                session = async_get_clientsession(self.hass)
                url = f"{API_BASE_URL}{AUTH_REFRESH_TOKEN}"

                payload = {"refreshToken": self._refresh_token}
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "napper/260819.092737 CFNetwork/3892.100.1 Darwin/27.0.0",
                    "device": self._device_id,
                    "source": "APP",
                    "locale": "en-US",
                    "language": "en",
                }

                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    if response.status != 200:
                        error_data = await parse_json_response(response)
                        if is_permanent_refresh_error(response.status, error_data):
                            raise ConfigEntryAuthFailed(
                                "Refresh token is invalid or expired"
                            )
                        raise UpdateFailed(
                            f"Token refresh failed with status {response.status}"
                        )

                    data = await parse_json_response(response)
                    if data is None:
                        raise UpdateFailed("Empty response from token refresh")
                    item = data.get("item", {})

                    id_token_data = item.get("idToken", {})
                    refresh_token_data = item.get("refreshToken", {})

                    new_id_token = id_token_data.get("token", "")
                    new_refresh_token = refresh_token_data.get("token", "")
                    id_token_payload = id_token_data.get("payload", {})
                    new_expiry = id_token_payload.get("exp")

                    if not new_id_token:
                        raise UpdateFailed("No ID token in refresh response")

                    self._token = new_id_token
                    if new_refresh_token:
                        self._refresh_token = new_refresh_token
                    try:
                        self._token_expiry = int(new_expiry)
                    except (TypeError, ValueError):
                        self._token_expiry = (
                            int(datetime.now().timestamp()) + DEFAULT_TOKEN_LIFETIME
                        )

                    new_data = {**self.entry.data}
                    new_data[CONF_ID_TOKEN] = self._token
                    new_data[CONF_REFRESH_TOKEN] = self._refresh_token
                    new_data[CONF_TOKEN_EXPIRY] = self._token_expiry
                    self.hass.config_entries.async_update_entry(
                        self.entry, data=new_data
                    )

                    _LOGGER.info(
                        "Token refreshed successfully, expires at %s",
                        datetime.fromtimestamp(self._token_expiry),
                    )

            except ConfigEntryAuthFailed:
                raise
            except UpdateFailed:
                raise
            except asyncio.TimeoutError as err:
                raise UpdateFailed("Token refresh timed out") from err
            except aiohttp.ClientError as err:
                raise UpdateFailed(f"Error refreshing token: {err}") from err
            except Exception as err:
                raise UpdateFailed(f"Unexpected error refreshing token: {err}") from err

    async def _async_update_data(self) -> dict:
        """Fetch data from Napper API."""
        try:
            # Ensure we have a valid token
            await self._refresh_token_if_needed()
            
            session = async_get_clientsession(self.hass)
            
            # Build the URL with current timestamp
            now = datetime.now().astimezone().isoformat(timespec='milliseconds')
            url = f"{API_BASE_URL}{ENDPOINT_WIDGET_TODAY}/{self.baby_id}/{now}"
            
            headers = {
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            }
            
            _LOGGER.debug("Fetching data from %s", url)
            
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 401:
                    # Token might be expired, try refresh
                    _LOGGER.warning("Received 401, attempting token refresh")
                    await self._refresh_token_if_needed(force=True)
                    headers["Authorization"] = f"Bearer {self._token}"
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as retry_response:
                        if retry_response.status == 401:
                            raise ConfigEntryAuthFailed(
                                "Authentication failed after token refresh"
                            )
                        retry_response.raise_for_status()
                        data = await parse_json_response(retry_response)
                        if data is None:
                            raise UpdateFailed("Empty response from API")
                        return self._parse_api_response(data.get("item", {}))
                
                response.raise_for_status()
                
                # API returns text/plain instead of application/json
                data = await parse_json_response(response)
                if data is None:
                    raise UpdateFailed("Empty response from API")
                
                _LOGGER.debug("Received data: %s", data)
                
                return self._parse_api_response(data.get("item", {}))
                
        except (ConfigEntryAuthFailed, UpdateFailed):
            raise
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout fetching data: {err}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
        except json.JSONDecodeError as err:
            raise UpdateFailed(f"Invalid JSON response: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    def _parse_api_response(self, item: dict) -> dict:
        """Parse API response into structured data."""
        logs = item.get("logs", [])
        schedule_items = item.get("scheduleItems", [])
        
        # Sort logs by creation time (newest first)
        logs_sorted = sorted(
            logs,
            key=lambda x: x.get("createdAt", ""),
            reverse=True
        )
        
        # Find current sleeping state
        # Priority 1: Open NAP log (explicit sleep tracking)
        # Priority 2: BED_TIME log without subsequent WOKE_UP (bedtime routine started)
        baby_sleeping = False
        current_nap = None
        for log in logs:
            if log.get("category") == "NAP" and log.get("isOpen", False):
                baby_sleeping = True
                current_nap = log
                # Match with schedule item to get duration
                current_nap = self._match_nap_with_schedule(log, schedule_items)
                break
        
        # If no open NAP, check if bedtime was started but not yet woken up
        if not baby_sleeping:
            last_bedtime_log = None
            last_wake_up_log = None
            for log in logs:
                if log.get("category") == "BED_TIME" and last_bedtime_log is None:
                    last_bedtime_log = log
                elif log.get("category") == "WOKE_UP" and last_wake_up_log is None:
                    last_wake_up_log = log
            
            # Baby is sleeping if bedtime was logged and no wake-up since then
            if last_bedtime_log is not None:
                bedtime_created = last_bedtime_log.get("createdAt", "")
                if last_wake_up_log is None:
                    baby_sleeping = True
                else:
                    wake_up_created = last_wake_up_log.get("createdAt", "")
                    # Compare timestamps - bedtime after wake-up means still sleeping
                    if bedtime_created > wake_up_created:
                        baby_sleeping = True
        
        # Get most recent logs by category
        last_diaper = None
        last_solids = None
        last_wake_up = None
        last_bedtime = None
        last_nursing = None
        
        # Track last diaper change by type
        last_wet_diaper = None
        last_dry_diaper = None
        last_mixed_diaper = None
        last_dirty_diaper = None
        
        for log in logs_sorted:
            category = log.get("category")
            if category == "CHANGED_DIAPER":
                if last_diaper is None:
                    last_diaper = log
                # Track by diaper content type
                diaper_content = log.get("diaperContent", "")
                if diaper_content == "WET" and last_wet_diaper is None:
                    last_wet_diaper = log
                elif diaper_content == "DRY" and last_dry_diaper is None:
                    last_dry_diaper = log
                elif diaper_content == "MIXED" and last_mixed_diaper is None:
                    last_mixed_diaper = log
                elif diaper_content == "POOP" and last_dirty_diaper is None:
                    last_dirty_diaper = log
            elif category == "SOLIDS" and last_solids is None:
                last_solids = log
            elif category == "WOKE_UP" and last_wake_up is None:
                last_wake_up = log
            elif category == "BED_TIME" and last_bedtime is None:
                last_bedtime = log
            elif category == "NURSING" and last_nursing is None:
                last_nursing = log
        
        # Get next scheduled events
        next_nap = None
        next_bedtime = None
        for schedule_item in schedule_items:
            if schedule_item.get("type") == "NAP" and not schedule_item.get("completed", False):
                if next_nap is None:
                    next_nap = schedule_item
            elif schedule_item.get("type") == "BED_TIME" and not schedule_item.get("completed", False):
                if next_bedtime is None:
                    next_bedtime = schedule_item
        
        return {
            "baby_sleeping": baby_sleeping,
            "current_nap": current_nap,
            "last_diaper": last_diaper,
            "last_wet_diaper": last_wet_diaper,
            "last_dry_diaper": last_dry_diaper,
            "last_mixed_diaper": last_mixed_diaper,
            "last_dirty_diaper": last_dirty_diaper,
            "last_solids": last_solids,
            "last_wake_up": last_wake_up,
            "last_bedtime": last_bedtime,
            "last_nursing": last_nursing,
            "next_nap": next_nap,
            "next_bedtime": next_bedtime,
            "all_logs": logs,
            "schedule_items": schedule_items,
        }

    def _match_nap_with_schedule(self, nap_log: dict, schedule_items: list) -> dict:
        """Match a nap log with its corresponding schedule item to get duration.
        
        The API returns schedule items with duration info. We match by finding
        the schedule item whose time is closest to the nap's start time.
        
        Schedule times from API are naive (no timezone) and represent local time.
        Nap start times are timezone-aware (e.g., "2026-09-03T10:46:17.127+02:00").
        We use HA's timezone utilities to properly handle the conversion.
        """
        nap_start = nap_log.get("start", "")
        if not nap_start:
            return nap_log
        
        try:
            # Parse nap start time (API returns timezone-aware)
            nap_start_dt = datetime.fromisoformat(nap_start.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return nap_log
        
        # Get Home Assistant's local timezone for converting naive schedule times
        from homeassistant.util.dt import now as dt_now
        local_tz = dt_now().tzinfo
        
        # Find the schedule item with the closest time to nap start
        best_match = None
        best_diff = None
        
        for schedule_item in schedule_items:
            if schedule_item.get("type") != "NAP":
                continue
            
            schedule_time = schedule_item.get("time", "")
            if not schedule_time:
                continue
            
            try:
                # Schedule times are naive (no timezone), e.g., "2026-09-03T10:57:00.000"
                # The .replace("Z", "+00:00") won't help since there's no Z suffix
                schedule_dt = datetime.fromisoformat(schedule_time.replace("Z", "+00:00"))
                
                # Make schedule_dt timezone-aware using HA's local timezone
                # This is the correct approach since API returns times in user's local timezone
                if schedule_dt.tzinfo is None and local_tz is not None:
                    schedule_dt = schedule_dt.replace(tzinfo=local_tz)
            except (ValueError, AttributeError):
                continue
            
            # Calculate time difference (both should now be timezone-aware)
            diff = abs((nap_start_dt - schedule_dt).total_seconds())
            
            # Match if within 30 minutes (adjustable threshold)
            if diff < 30 * 60:
                if best_diff is None or diff < best_diff:
                    best_diff = diff
                    best_match = schedule_item
        
        # Merge schedule data into nap log
        if best_match:
            scheduled_duration = best_match.get("duration")
            _LOGGER.debug(
                "Matched nap %s with schedule item: duration=%s, napNumber=%s",
                nap_log.get("id"),
                scheduled_duration,
                best_match.get("napNumber"),
            )
            return {
                **nap_log,
                "scheduled_duration": scheduled_duration,
                "scheduled_nap_number": best_match.get("napNumber"),
            }
        
        _LOGGER.debug("No matching schedule item found for nap %s", nap_log.get("id"))
        return nap_log
