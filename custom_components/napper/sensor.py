"""Sensor platform for Napper integration."""

from datetime import datetime, timedelta
import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.typing import StateType
from homeassistant.util.dt import now as dt_now

from .const import DOMAIN, CONF_BABY_NAME
from .coordinator import NapperDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: NapperDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    baby_name = entry.data.get(CONF_BABY_NAME, "Baby")
    
    entities = [
        NapperLastDiaperChangeSensor(coordinator, baby_name),
        NapperLastDiaperContentSensor(coordinator, baby_name),
        NapperLastWetDiaperSensor(coordinator, baby_name),
        NapperLastDryDiaperSensor(coordinator, baby_name),
        NapperLastMixedDiaperSensor(coordinator, baby_name),
        NapperLastDirtyDiaperSensor(coordinator, baby_name),
        NapperLastSolidsSensor(coordinator, baby_name),
        NapperLastWakeUpSensor(coordinator, baby_name),
        NapperLastBedtimeSensor(coordinator, baby_name),
        NapperNextNapSensor(coordinator, baby_name),
        NapperNextBedtimeSensor(coordinator, baby_name),
        NapperCurrentNapSensor(coordinator, baby_name),
        NapperNapDurationSensor(coordinator, baby_name),
        NapperNapEndTimeSensor(coordinator, baby_name),
        NapperBedtimeEndTimeSensor(coordinator, baby_name),
    ]
    
    async_add_entities(entities)


class NapperLastDiaperChangeSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last diaper change timestamp."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: NapperDataUpdateCoordinator, baby_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._baby_name = baby_name
        self._attr_unique_id = f"{coordinator.baby_id}_last_diaper_change"
        self._attr_name = f"{baby_name} Last Diaper Change"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.baby_id)},
            "name": baby_name,
            "manufacturer": "Napper",
        }

    @property
    def native_value(self) -> datetime | None:
        """Return the last diaper change timestamp."""
        if not self.coordinator.data:
            return None
        
        last_diaper = self.coordinator.data.get("last_diaper")
        if not last_diaper:
            return None
        
        start = last_diaper.get("start")
        if start:
            try:
                return datetime.fromisoformat(start.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return additional attributes."""
        if not self.coordinator.data:
            return None
        
        last_diaper = self.coordinator.data.get("last_diaper")
        if not last_diaper:
            return None
        
        return {
            "diaper_content": last_diaper.get("diaperContent"),
            "log_id": last_diaper.get("id"),
            "comment": last_diaper.get("comment", ""),
        }


class NapperLastDiaperContentSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last diaper content type."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NapperDataUpdateCoordinator, baby_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._baby_name = baby_name
        self._attr_unique_id = f"{coordinator.baby_id}_last_diaper_content"
        self._attr_name = f"{baby_name} Last Diaper Content"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.baby_id)},
            "name": baby_name,
            "manufacturer": "Napper",
        }

    @property
    def native_value(self) -> str | None:
        """Return the last diaper content type."""
        if not self.coordinator.data:
            return None
        
        last_diaper = self.coordinator.data.get("last_diaper")
        if not last_diaper:
            return None
        
        return last_diaper.get("diaperContent")

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return additional attributes."""
        if not self.coordinator.data:
            return None
        
        last_diaper = self.coordinator.data.get("last_diaper")
        if not last_diaper:
            return None
        
        return {
            "timestamp": last_diaper.get("start"),
            "log_id": last_diaper.get("id"),
        }


class NapperLastWetDiaperSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last wet diaper change timestamp."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: NapperDataUpdateCoordinator, baby_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._baby_name = baby_name
        self._attr_unique_id = f"{coordinator.baby_id}_last_wet_diaper"
        self._attr_name = f"{baby_name} Last Wet Diaper"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.baby_id)},
            "name": baby_name,
            "manufacturer": "Napper",
        }

    @property
    def native_value(self) -> datetime | None:
        """Return the last wet diaper change timestamp."""
        if not self.coordinator.data:
            return None
        
        last_wet = self.coordinator.data.get("last_wet_diaper")
        if not last_wet:
            return None
        
        start = last_wet.get("start")
        if start:
            try:
                return datetime.fromisoformat(start.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None
        return None


class NapperLastDryDiaperSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last dry diaper change timestamp."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: NapperDataUpdateCoordinator, baby_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._baby_name = baby_name
        self._attr_unique_id = f"{coordinator.baby_id}_last_dry_diaper"
        self._attr_name = f"{baby_name} Last Dry Diaper"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.baby_id)},
            "name": baby_name,
            "manufacturer": "Napper",
        }

    @property
    def native_value(self) -> datetime | None:
        """Return the last dry diaper change timestamp."""
        if not self.coordinator.data:
            return None
        
        last_dry = self.coordinator.data.get("last_dry_diaper")
        if not last_dry:
            return None
        
        start = last_dry.get("start")
        if start:
            try:
                return datetime.fromisoformat(start.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None
        return None


class NapperLastMixedDiaperSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last mixed diaper change timestamp."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: NapperDataUpdateCoordinator, baby_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._baby_name = baby_name
        self._attr_unique_id = f"{coordinator.baby_id}_last_mixed_diaper"
        self._attr_name = f"{baby_name} Last Mixed Diaper"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.baby_id)},
            "name": baby_name,
            "manufacturer": "Napper",
        }

    @property
    def native_value(self) -> datetime | None:
        """Return the last mixed diaper change timestamp."""
        if not self.coordinator.data:
            return None
        
        last_mixed = self.coordinator.data.get("last_mixed_diaper")
        if not last_mixed:
            return None
        
        start = last_mixed.get("start")
        if start:
            try:
                return datetime.fromisoformat(start.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None
        return None


class NapperLastDirtyDiaperSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last dirty diaper (POOP) change timestamp."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: NapperDataUpdateCoordinator, baby_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._baby_name = baby_name
        self._attr_unique_id = f"{coordinator.baby_id}_last_dirty_diaper"
        self._attr_name = f"{baby_name} Last Dirty Diaper"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.baby_id)},
            "name": baby_name,
            "manufacturer": "Napper",
        }

    @property
    def native_value(self) -> datetime | None:
        """Return the last dirty diaper change timestamp."""
        if not self.coordinator.data:
            return None
        
        last_dirty = self.coordinator.data.get("last_dirty_diaper")
        if not last_dirty:
            return None
        
        start = last_dirty.get("start")
        if start:
            try:
                return datetime.fromisoformat(start.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None
        return None


class NapperLastSolidsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last solid food feeding timestamp."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: NapperDataUpdateCoordinator, baby_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._baby_name = baby_name
        self._attr_unique_id = f"{coordinator.baby_id}_last_solids"
        self._attr_name = f"{baby_name} Last Solid Food"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.baby_id)},
            "name": baby_name,
            "manufacturer": "Napper",
        }

    @property
    def native_value(self) -> datetime | None:
        """Return the last solids timestamp."""
        if not self.coordinator.data:
            return None
        
        last_solids = self.coordinator.data.get("last_solids")
        if not last_solids:
            return None
        
        start = last_solids.get("start")
        if start:
            try:
                return datetime.fromisoformat(start.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None
        return None


class NapperLastWakeUpSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last wake up timestamp."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: NapperDataUpdateCoordinator, baby_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._baby_name = baby_name
        self._attr_unique_id = f"{coordinator.baby_id}_last_wake_up"
        self._attr_name = f"{baby_name} Last Wake Up"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.baby_id)},
            "name": baby_name,
            "manufacturer": "Napper",
        }

    @property
    def native_value(self) -> datetime | None:
        """Return the last wake up timestamp."""
        if not self.coordinator.data:
            return None
        
        last_wake_up = self.coordinator.data.get("last_wake_up")
        if not last_wake_up:
            return None
        
        start = last_wake_up.get("start")
        if start:
            try:
                return datetime.fromisoformat(start.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None
        return None


class NapperLastBedtimeSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last bedtime timestamp."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: NapperDataUpdateCoordinator, baby_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._baby_name = baby_name
        self._attr_unique_id = f"{coordinator.baby_id}_last_bedtime"
        self._attr_name = f"{baby_name} Last Bedtime"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.baby_id)},
            "name": baby_name,
            "manufacturer": "Napper",
        }

    @property
    def native_value(self) -> datetime | None:
        """Return the last bedtime timestamp."""
        if not self.coordinator.data:
            return None
        
        last_bedtime = self.coordinator.data.get("last_bedtime")
        if not last_bedtime:
            return None
        
        start = last_bedtime.get("start")
        if start:
            try:
                return datetime.fromisoformat(start.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None
        return None


class NapperNextNapSensor(CoordinatorEntity, SensorEntity):
    """Sensor for next scheduled nap time."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: NapperDataUpdateCoordinator, baby_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._baby_name = baby_name
        self._attr_unique_id = f"{coordinator.baby_id}_next_nap"
        self._attr_name = f"{baby_name} Next Nap"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.baby_id)},
            "name": baby_name,
            "manufacturer": "Napper",
        }

    @property
    def native_value(self) -> datetime | None:
        """Return the next nap time."""
        if not self.coordinator.data:
            return None
        
        next_nap = self.coordinator.data.get("next_nap")
        if not next_nap:
            return None
        
        time = next_nap.get("time")
        if time:
            try:
                # Handle both timezone-aware and naive datetimes
                if time.endswith("Z"):
                    time = time.replace("Z", "+00:00")
                dt = datetime.fromisoformat(time)
                # If naive datetime, make it timezone-aware using local timezone
                if dt.tzinfo is None:
                    local_tz = dt_now().tzinfo
                    if local_tz:
                        dt = dt.replace(tzinfo=local_tz)
                return dt
            except (ValueError, AttributeError):
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return additional attributes."""
        if not self.coordinator.data:
            return None
        
        next_nap = self.coordinator.data.get("next_nap")
        if not next_nap:
            return None
        
        return {
            "nap_number": next_nap.get("napNumber"),
            "duration_minutes": next_nap.get("duration"),
            "completed": next_nap.get("completed"),
        }


class NapperNextBedtimeSensor(CoordinatorEntity, SensorEntity):
    """Sensor for next scheduled bedtime."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: NapperDataUpdateCoordinator, baby_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._baby_name = baby_name
        self._attr_unique_id = f"{coordinator.baby_id}_next_bedtime"
        self._attr_name = f"{baby_name} Next Bedtime"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.baby_id)},
            "name": baby_name,
            "manufacturer": "Napper",
        }

    @property
    def native_value(self) -> datetime | None:
        """Return the next bedtime."""
        if not self.coordinator.data:
            return None
        
        next_bedtime = self.coordinator.data.get("next_bedtime")
        if not next_bedtime:
            return None
        
        time = next_bedtime.get("time")
        if time:
            try:
                # Handle both timezone-aware and naive datetimes
                if time.endswith("Z"):
                    time = time.replace("Z", "+00:00")
                dt = datetime.fromisoformat(time)
                # If naive datetime, make it timezone-aware using local timezone
                if dt.tzinfo is None:
                    local_tz = dt_now().tzinfo
                    if local_tz:
                        dt = dt.replace(tzinfo=local_tz)
                return dt
            except (ValueError, AttributeError):
                return None
        return None


class NapperCurrentNapSensor(CoordinatorEntity, SensorEntity):
    """Sensor for current nap in progress."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: NapperDataUpdateCoordinator, baby_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._baby_name = baby_name
        self._attr_unique_id = f"{coordinator.baby_id}_current_nap"
        self._attr_name = f"{baby_name} Current Nap"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.baby_id)},
            "name": baby_name,
            "manufacturer": "Napper",
        }

    @property
    def native_value(self) -> datetime | None:
        """Return the current nap start time, or None if baby is not napping."""
        if not self.coordinator.data:
            return None
        
        current_nap = self.coordinator.data.get("current_nap")
        if not current_nap:
            return None
        
        start = current_nap.get("start")
        if start:
            try:
                # Handle both timezone-aware and naive datetimes
                if start.endswith("Z"):
                    start = start.replace("Z", "+00:00")
                dt = datetime.fromisoformat(start)
                # If naive datetime, make it timezone-aware using local timezone
                if dt.tzinfo is None:
                    local_tz = dt_now().tzinfo
                    if local_tz:
                        dt = dt.replace(tzinfo=local_tz)
                return dt
            except (ValueError, AttributeError):
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return additional attributes about the current nap."""
        if not self.coordinator.data:
            return None
        
        current_nap = self.coordinator.data.get("current_nap")
        if not current_nap:
            return None
        
        attributes = {
            "log_id": current_nap.get("id"),
            "category": current_nap.get("category"),
            "is_open": current_nap.get("isOpen"),
            "comment": current_nap.get("comment", ""),
        }
        
        # Add scheduled duration if available
        scheduled_duration = current_nap.get("scheduled_duration")
        _LOGGER.debug(
            "Current nap sensor: scheduled_duration=%s, start=%s",
            scheduled_duration,
            current_nap.get("start"),
        )
        if scheduled_duration is not None:
            attributes["expected_duration_minutes"] = scheduled_duration
        
        # Calculate expected end time (start + scheduled duration)
        start_str = current_nap.get("start")
        if start_str:
            try:
                start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                if start_dt.tzinfo is None:
                    local_tz = dt_now().tzinfo
                    if local_tz:
                        start_dt = start_dt.replace(tzinfo=local_tz)
                
                # Only calculate expected_end_time if we have a valid duration
                if scheduled_duration is not None and isinstance(scheduled_duration, (int, float)):
                    expected_end = start_dt + timedelta(minutes=scheduled_duration)
                    attributes["expected_end_time"] = expected_end
                    _LOGGER.debug(
                        "Calculated expected_end_time: start=%s + duration=%s min = %s",
                        start_dt,
                        scheduled_duration,
                        expected_end,
                    )
                else:
                    _LOGGER.debug(
                        "Cannot calculate expected_end_time: scheduled_duration=%s (type: %s)",
                        scheduled_duration,
                        type(scheduled_duration).__name__ if scheduled_duration is not None else "None",
                    )
            except (ValueError, AttributeError, TypeError) as err:
                _LOGGER.error("Failed to calculate expected_end_time: %s", err)
        
        # Calculate current duration (elapsed time since start)
        if start_str:
            try:
                start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                if start_dt.tzinfo is None:
                    local_tz = dt_now().tzinfo
                    if local_tz:
                        start_dt = start_dt.replace(tzinfo=local_tz)
                
                now = dt_now()
                elapsed = now - start_dt
                elapsed_minutes = int(elapsed.total_seconds() / 60)
                attributes["current_duration_minutes"] = elapsed_minutes
            except (ValueError, AttributeError):
                pass
        
        return attributes


class NapperNapDurationSensor(CoordinatorEntity, SensorEntity):
    """Sensor for nap duration - shows current nap duration or next scheduled nap duration."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NapperDataUpdateCoordinator, baby_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._baby_name = baby_name
        self._attr_unique_id = f"{coordinator.baby_id}_nap_expected_duration"
        self._attr_name = f"{baby_name} Nap Expected Duration"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.baby_id)},
            "name": baby_name,
            "manufacturer": "Napper",
        }

    @property
    def native_value(self) -> int | None:
        """Return the expected nap duration in minutes.
        
        Priority:
        1. Current nap scheduled duration (if baby is napping)
        2. Next scheduled nap duration (if not napping)
        3. None if no data available
        """
        if not self.coordinator.data:
            return None
        
        # First, check if baby is currently napping
        current_nap = self.coordinator.data.get("current_nap")
        if current_nap:
            scheduled_duration = current_nap.get("scheduled_duration")
            if scheduled_duration is not None:
                return int(scheduled_duration)
        
        # Fall back to next scheduled nap
        next_nap = self.coordinator.data.get("next_nap")
        if next_nap:
            duration = next_nap.get("duration")
            if duration is not None:
                return int(duration)
        
        return None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return additional attributes."""
        if not self.coordinator.data:
            return None
        
        attrs = {"source": "unavailable"}
        
        # Check current nap first
        current_nap = self.coordinator.data.get("current_nap")
        if current_nap:
            scheduled_duration = current_nap.get("scheduled_duration")
            if scheduled_duration is not None:
                attrs = {
                    "source": "current_nap",
                    "scheduled_duration_minutes": scheduled_duration,
                    "nap_start": current_nap.get("start"),
                }
                return attrs
        
        # Fall back to next nap
        next_nap = self.coordinator.data.get("next_nap")
        if next_nap:
            duration = next_nap.get("duration")
            if duration is not None:
                attrs = {
                    "source": "next_scheduled_nap",
                    "scheduled_duration_minutes": duration,
                    "nap_number": next_nap.get("napNumber"),
                    "scheduled_time": next_nap.get("time"),
                }
                return attrs
        
        return attrs


class NapperNapEndTimeSensor(CoordinatorEntity, SensorEntity):
    """Sensor for nap end time - shows expected end of current nap or next scheduled nap."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: NapperDataUpdateCoordinator, baby_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._baby_name = baby_name
        self._attr_unique_id = f"{coordinator.baby_id}_nap_expected_end_time"
        self._attr_name = f"{baby_name} Nap Expected End Time"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.baby_id)},
            "name": baby_name,
            "manufacturer": "Napper",
        }

    @property
    def native_value(self) -> datetime | None:
        """Return the expected nap end time.
        
        Priority:
        1. Current nap end time (start + scheduled duration) if baby is napping
        2. Next scheduled nap end time (time + duration) if not napping
        3. None if no data available
        """
        if not self.coordinator.data:
            return None
        
        # Check current nap first
        current_nap = self.coordinator.data.get("current_nap")
        if current_nap:
            start_str = current_nap.get("start")
            scheduled_duration = current_nap.get("scheduled_duration")
            if start_str and scheduled_duration is not None:
                try:
                    start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    if start_dt.tzinfo is None:
                        local_tz = dt_now().tzinfo
                        if local_tz:
                            start_dt = start_dt.replace(tzinfo=local_tz)
                    return start_dt + timedelta(minutes=scheduled_duration)
                except (ValueError, AttributeError, TypeError):
                    pass
        
        # Fall back to next scheduled nap
        next_nap = self.coordinator.data.get("next_nap")
        if next_nap:
            time_str = next_nap.get("time")
            duration = next_nap.get("duration")
            if time_str and duration is not None:
                try:
                    if time_str.endswith("Z"):
                        time_str = time_str.replace("Z", "+00:00")
                    time_dt = datetime.fromisoformat(time_str)
                    if time_dt.tzinfo is None:
                        local_tz = dt_now().tzinfo
                        if local_tz:
                            time_dt = time_dt.replace(tzinfo=local_tz)
                    return time_dt + timedelta(minutes=duration)
                except (ValueError, AttributeError, TypeError):
                    pass
        
        return None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return additional attributes."""
        if not self.coordinator.data:
            return None
        
        attrs = {"source": "unavailable"}
        
        # Check current nap first
        current_nap = self.coordinator.data.get("current_nap")
        if current_nap:
            start_str = current_nap.get("start")
            scheduled_duration = current_nap.get("scheduled_duration")
            if start_str and scheduled_duration is not None:
                return {
                    "source": "current_nap",
                    "nap_start": start_str,
                    "scheduled_duration_minutes": scheduled_duration,
                    "log_id": current_nap.get("id"),
                }
        
        # Fall back to next nap
        next_nap = self.coordinator.data.get("next_nap")
        if next_nap:
            time_str = next_nap.get("time")
            duration = next_nap.get("duration")
            if time_str and duration is not None:
                return {
                    "source": "next_scheduled_nap",
                    "scheduled_time": time_str,
                    "scheduled_duration_minutes": duration,
                    "nap_number": next_nap.get("napNumber"),
                }
        
        return attrs


class NapperBedtimeEndTimeSensor(CoordinatorEntity, SensorEntity):
    """Sensor for bedtime - shows expected bedtime from schedule."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: NapperDataUpdateCoordinator, baby_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._baby_name = baby_name
        self._attr_unique_id = f"{coordinator.baby_id}_bedtime_expected_time"
        self._attr_name = f"{baby_name} Bedtime Expected Time"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.baby_id)},
            "name": baby_name,
            "manufacturer": "Napper",
        }

    @property
    def native_value(self) -> datetime | None:
        """Return the expected bedtime.
        
        Returns the next scheduled bedtime from the schedule.
        """
        if not self.coordinator.data:
            return None
        
        next_bedtime = self.coordinator.data.get("next_bedtime")
        if not next_bedtime:
            return None
        
        time = next_bedtime.get("time")
        if time:
            try:
                # Handle both timezone-aware and naive datetimes
                if time.endswith("Z"):
                    time = time.replace("Z", "+00:00")
                dt = datetime.fromisoformat(time)
                # If naive datetime, make it timezone-aware using local timezone
                if dt.tzinfo is None:
                    local_tz = dt_now().tzinfo
                    if local_tz:
                        dt = dt.replace(tzinfo=local_tz)
                return dt
            except (ValueError, AttributeError):
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return additional attributes."""
        if not self.coordinator.data:
            return None
        
        next_bedtime = self.coordinator.data.get("next_bedtime")
        if not next_bedtime:
            return None
        
        return {
            "scheduled_time": next_bedtime.get("time"),
            "completed": next_bedtime.get("completed"),
        }
