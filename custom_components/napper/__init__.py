"""Napper Baby Tracking integration for Home Assistant."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_ID_TOKEN, CONF_TOKEN

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]
SERVICE_REGISTRY_KEY = f"{DOMAIN}_services"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Napper component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Napper from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(SERVICE_REGISTRY_KEY, [])
    
    # Migrate old token key to new id_token key if needed
    data = dict(entry.data)
    if CONF_TOKEN in data and CONF_ID_TOKEN not in data:
        # Old config with single "token" key
        data[CONF_ID_TOKEN] = data[CONF_TOKEN]
        # Don't remove CONF_TOKEN to maintain backward compatibility
        hass.config_entries.async_update_entry(entry, data=data)
    
    # Create the Napper coordinator
    from .coordinator import NapperDataUpdateCoordinator
    
    coordinator = NapperDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services
    await _register_services(hass, coordinator)
    
    # Store coordinator reference for service unregistration
    hass.data[DOMAIN][SERVICE_REGISTRY_KEY].append(coordinator)
    
    return True


async def _register_services(hass: HomeAssistant, coordinator) -> None:
    """Register Napper services."""
    from .services import async_register_services
    await async_register_services(hass, coordinator)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Unregister services
        from .services import async_unregister_services
        await async_unregister_services(hass)
        
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry to new format."""
    if config_entry.version == 1:
        # Migrate from old token-only format to new OTP format
        data = dict(config_entry.data)
        
        # If we have old "token" key but not new keys, migrate
        if CONF_TOKEN in data and CONF_ID_TOKEN not in data:
            data[CONF_ID_TOKEN] = data[CONF_TOKEN]
            config_entry.version = 1  # Same version, just updated data
            hass.config_entries.async_update_entry(config_entry, data=data)
    
    return True
