"""Base class for Owlet entities."""

from datetime import datetime, timezone

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import OwletCoordinator


class OwletBaseEntity(CoordinatorEntity[OwletCoordinator], Entity):
    """Base class for Owlet Sock entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OwletCoordinator,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.sock = coordinator.sock

    @property
    def device_identifier(self) -> str:
        """New entries are region-scoped; legacy registries retain their IDs."""
        namespace = self.coordinator.config_entry.data.get("entity_namespace")
        return f"{namespace}_{self.sock.serial}" if namespace else self.sock.serial

    def entity_unique_id(self, key: str) -> str:
        return f"{self.device_identifier}-{key}"

    @property
    def available(self) -> bool:
        """Require timestamp evidence for timestamped v3 measurements."""
        if not super().available:
            return False
        key = getattr(getattr(self, "entity_description", None), "key", None)
        vitals = {"heart_rate", "oxygen_saturation", "oxygen_10_av", "sleep_state",
                  "skin_temperature", "movement", "movement_bucket", "battery_minutes",
                  "battery_percentage", "charging", "base_station_on"}
        if self.sock.version != 3 or key not in vitals:
            return True
        try:
            stamp = datetime.fromisoformat(self.sock.properties["last_updated"])
            if stamp.tzinfo is None:
                return False
            age = (datetime.now(timezone.utc) - stamp).total_seconds()
            # A local freshness policy, not a claimed Owlet update SLA.
            return 0 <= age <= max(120, self.coordinator.update_interval.total_seconds() * 3)
        except (KeyError, TypeError, ValueError):
            return False

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info of the device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.device_identifier)},
            name=f"Owlet Sock {self.sock.serial}",
            connections={("mac", self.sock.mac)} if self.sock.mac else set(),
            suggested_area="Nursery",
            configuration_url="https://my.owletcare.com/",
            manufacturer="Owlet Baby Care",
            model=getattr(self.sock, "model", None),
            sw_version=getattr(self.sock, "sw_version", None),
            hw_version=str(self.sock.revision) if self.sock.revision is not None else None,
        )
