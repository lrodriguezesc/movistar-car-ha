from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MovistarCarCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MovistarCarCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([MovistarCarTracker(coordinator)])


class MovistarCarTracker(CoordinatorEntity[MovistarCarCoordinator], TrackerEntity):
    _attr_has_entity_name = True
    _attr_name = "Location"
    _attr_icon = "mdi:car"

    def __init__(self, coordinator: MovistarCarCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_tracker"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(coordinator.device_id))},
            "name": coordinator.vehicle_name,
            "manufacturer": "Movistar",
            "model": "Car Connected Device",
            "serial_number": coordinator.serial,
        }

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.data.get("latitude")

    @property
    def longitude(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.data.get("longitude")

    @property
    def extra_state_attributes(self) -> dict:
        if self.coordinator.data is None:
            return {}
        data = self.coordinator.data.data
        attrs = {}
        if data.get("heading") is not None:
            attrs["heading"] = data["heading"]
        if data.get("speed") is not None:
            attrs["speed"] = data["speed"]
        if data.get("valid_position") is not None:
            attrs["gps_valid"] = data["valid_position"]
        return attrs
