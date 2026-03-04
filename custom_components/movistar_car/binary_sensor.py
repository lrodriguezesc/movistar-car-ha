from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MovistarCarCoordinator, MovistarCarData


@dataclass(frozen=True, kw_only=True)
class MovistarCarBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[dict], bool | None]


BINARY_SENSOR_DESCRIPTIONS: list[MovistarCarBinarySensorDescription] = [
    MovistarCarBinarySensorDescription(
        key="connected",
        translation_key="connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:car-connected",
        value_fn=lambda d: d.get("connected"),
    ),
    MovistarCarBinarySensorDescription(
        key="errors",
        translation_key="errors",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:engine",
        value_fn=lambda d: d.get("errors"),
    ),
    MovistarCarBinarySensorDescription(
        key="wifi_enabled",
        translation_key="wifi_enabled",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:wifi",
        value_fn=lambda d: d.get("wifi_enabled"),
    ),
    MovistarCarBinarySensorDescription(
        key="valid_position",
        translation_key="valid_position",
        icon="mdi:crosshairs-gps",
        value_fn=lambda d: d.get("valid_position"),
    ),
    MovistarCarBinarySensorDescription(
        key="moving",
        translation_key="moving",
        device_class=BinarySensorDeviceClass.MOVING,
        icon="mdi:car-speed-limiter",
        value_fn=lambda d: d.get("moving"),
    ),
    MovistarCarBinarySensorDescription(
        key="incompatible",
        translation_key="incompatible",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:car-off",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("incompatible"),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MovistarCarCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        MovistarCarBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class MovistarCarBinarySensor(
    CoordinatorEntity[MovistarCarCoordinator], BinarySensorEntity
):
    _attr_has_entity_name = True
    entity_description: MovistarCarBinarySensorDescription

    def __init__(
        self,
        coordinator: MovistarCarCoordinator,
        description: MovistarCarBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{DOMAIN}_{coordinator.device_id}_{description.key}"
        )
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(coordinator.device_id))},
            "name": coordinator.vehicle_name,
            "manufacturer": "Movistar",
            "model": "Car Connected Device",
            "serial_number": coordinator.serial,
        }

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data.data)
