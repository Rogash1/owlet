"""Allowlisted diagnostics: never include config data, tokens or device identifiers."""
from .const import DOMAIN


async def async_get_config_entry_diagnostics(hass, entry):
    coordinators = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    return {
        'entry_version': entry.version,
        'devices': [
            {
                'generation': coordinator.sock.version,
                'last_update_success': coordinator.last_update_success,
                'poll_seconds': coordinator.update_interval.total_seconds(),
                'timestamp_available': 'last_updated' in coordinator.sock.properties,
            }
            for coordinator in coordinators.values()
        ],
    }
