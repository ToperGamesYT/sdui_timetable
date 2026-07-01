"""The Sdui integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SduiApiClient, SduiApiError, SduiAuthError
from .const import CONF_TOKEN, CONF_USER_ID, DOMAIN, PLATFORM_CALENDAR, PLATFORM_SENSOR
from .coordinator import SduiCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [PLATFORM_SENSOR, PLATFORM_CALENDAR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sdui from a config entry."""
    token = entry.data[CONF_TOKEN]
    user_id = entry.data.get(CONF_USER_ID)  # Get user_id from config entry
    session = async_get_clientsession(hass)

    client = SduiApiClient(token, session, user_id=user_id)
    coordinator = SduiCoordinator(hass, client)

    try:
        await coordinator.async_config_entry_first_refresh()
    except SduiAuthError as exc:
        raise ConfigEntryAuthFailed(str(exc)) from exc
    except SduiApiError as exc:
        raise ConfigEntryNotReady(str(exc)) from exc

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update (e.g., token renewal)."""
    await hass.config_entries.async_reload(entry.entry_id)
