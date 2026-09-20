"""Owlet integration coordinator class."""
from __future__ import annotations

from datetime import timedelta
import logging

from pyowletapi.exceptions import (
    OwletAuthenticationError,
    OwletConnectionError,
    OwletError,
)
from pyowletapi.sock import Sock

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, POLLING_INTERVAL

_LOGGER = logging.getLogger(__name__)


class OwletCoordinator(DataUpdateCoordinator):
    """Coordinator is responsible for querying the device at a specified route."""

    def __init__(
        self, hass: HomeAssistant, sock: Sock, interval, entry: ConfigEntry
    ) -> None:
        """Initialise a custom coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=max(5, interval or POLLING_INTERVAL)),
            config_entry=entry,
        )
        self.sock = sock
        self.config_entry: ConfigEntry = entry

    async def _async_update_data(self) -> None:
        """Fetch the data from the device."""
        try:
            await self.sock.update_properties()
        except OwletAuthenticationError as err:
            raise ConfigEntryAuthFailed("Owlet authentication failed") from err
        except OwletError as err:
            raise UpdateFailed("Unable to retrieve Owlet data") from err
        finally:
            tokens = self.sock.api.tokens
            if any(self.config_entry.data.get(key) != value for key, value in tokens.items()):
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data={**self.config_entry.data, **tokens}
                )
