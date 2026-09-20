"""The Owlet Smart Sock integration."""

from __future__ import annotations

import asyncio
import logging

from pyowletapi.api import OwletAPI
from pyowletapi.exceptions import (
    OwletAuthenticationError,
    OwletConnectionError,
    OwletDevicesError,
    OwletError,
)
from pyowletapi.sock import Sock

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_TOKEN,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_OWLET_EXPIRY, CONF_OWLET_REFRESH, DOMAIN, SUPPORTED_VERSIONS, POLLING_INTERVAL
from .coordinator import OwletCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]

_LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate only account identity; preserve device/entity IDs and history."""
    if entry.version > 2:
        return False
    if entry.version == 2:
        return True
    region = entry.data.get(CONF_REGION)
    username = entry.data.get(CONF_USERNAME)
    if region not in ("world", "europe") or not isinstance(username, str) or not username.strip():
        return False
    unique_id = f"{region}_{username.strip().lower()}"
    if any(other.entry_id != entry.entry_id and other.unique_id == unique_id
           for other in hass.config_entries.async_entries(DOMAIN)):
        return False
    hass.config_entries.async_update_entry(entry, unique_id=unique_id, version=2)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Owlet Smart Sock from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    owlet_api = OwletAPI(
        region=entry.data[CONF_REGION],
        token=entry.data[CONF_API_TOKEN],
        expiry=entry.data[CONF_OWLET_EXPIRY],
        refresh=entry.data[CONF_OWLET_REFRESH],
        session=async_get_clientsession(hass),
    )

    try:
        if token := await owlet_api.authenticate():
            hass.config_entries.async_update_entry(entry, data={**entry.data, **token})

        devices = await owlet_api.get_devices(SUPPORTED_VERSIONS)

    except OwletAuthenticationError as err:
        _LOGGER.error("Credentials no longer valid, please setup owlet again")
        raise ConfigEntryAuthFailed(
            "Credentials expired"
        ) from err

    except OwletConnectionError as err:
        raise ConfigEntryNotReady(
            "Error connecting to Owlet"
        ) from err

    except OwletDevicesError:
        _LOGGER.error("No owlet devices found to set up")
        return False
    except OwletError as err:
        raise ConfigEntryNotReady("Unable to retrieve Owlet data") from err
    finally:
        tokens = owlet_api.tokens
        if any(entry.data.get(key) != value for key, value in tokens.items()):
            hass.config_entries.async_update_entry(entry, data={**entry.data, **tokens})

    if "tokens" in devices:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, **devices["tokens"]}
        )

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, POLLING_INTERVAL)
    coordinators = {
        device["device"]["dsn"]: OwletCoordinator(
            hass, Sock(owlet_api, device["device"]), scan_interval, entry
        )
        for device in devices["response"]
    }

    await asyncio.gather(
        *(
            coordinator.async_config_entry_first_refresh()
            for coordinator in list(coordinators.values())
        )
    )

    hass.data[DOMAIN][entry.entry_id] = coordinators

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply options after unloading the previous polling tasks."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
