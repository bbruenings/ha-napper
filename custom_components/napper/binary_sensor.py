"""Binary sensor platform for Napper integration."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_BABY_NAME
from .coordinator import NapperDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator: NapperDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    baby_name = entry.data.get(CONF_BABY_NAME, "Baby")
    
    entities = [
        NapperBabySleepingSensor(coordinator, baby_name),
    ]
    
    async_add_entities(entities)


class NapperBabySleepingSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for baby sleeping state."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NapperDataUpdateCoordinator,
        baby_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._baby_name = baby_name
        self._attr_unique_id = f"{coordinator.baby_id}_sleeping"
        self._attr_name = f"{baby_name} Sleeping"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.baby_id)},
            "name": baby_name,
            "manufacturer": "Napper",
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if baby is sleeping."""
        return self.coordinator.data.get("baby_sleeping", False) if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return additional attributes."""
        if not self.coordinator.data:
            return None
        
        current_nap = self.coordinator.data.get("current_nap")
        if not current_nap:
            return None
        
        return {
            "nap_start": current_nap.get("start"),
            "nap_id": current_nap.get("id"),
            "comment": current_nap.get("comment", ""),
        }
