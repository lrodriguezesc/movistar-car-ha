from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfInformation,
    UnitOfLength,
    UnitOfSpeed,
    UnitOfVolume,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MovistarCarCoordinator, MovistarCarData


def _ms_to_datetime(value) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _ms_to_date(value) -> date | None:
    dt = _ms_to_datetime(value)
    return dt.date() if dt else None


def _itv_days_left(d: dict) -> int | None:
    due = _ms_to_date(d.get("next_itv_date"))
    return (due - date.today()).days if due else None


def _score_month(d: dict):
    """Score for the current month. The API uses -1 for months with no data."""
    scores = d.get("scoring_monthly")
    if not isinstance(scores, dict):
        return None
    today = date.today()
    months = scores.get(str(today.year)) or []
    value = months[today.month - 1] if len(months) >= today.month else None
    return value if value is not None and value >= 0 else None


def _score_history(d: dict) -> dict | None:
    scores = d.get("scoring_monthly")
    if not isinstance(scores, dict):
        return None
    return {
        f"{year}-{i + 1:02d}": v
        for year, months in scores.items()
        for i, v in enumerate(months)
        if v is not None and v >= 0
    }


@dataclass(frozen=True, kw_only=True)
class MovistarCarSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict], object]
    attrs_fn: Callable[[dict], dict | None] | None = None


SENSOR_DESCRIPTIONS: list[MovistarCarSensorDescription] = [
    MovistarCarSensorDescription(
        key="voltage",
        translation_key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        icon="mdi:car-battery",
        value_fn=lambda d: d.get("voltage"),
    ),
    MovistarCarSensorDescription(
        key="fuel",
        translation_key="fuel",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:gas-station",
        value_fn=lambda d: d.get("fuel"),
    ),
    MovistarCarSensorDescription(
        key="speed",
        translation_key="speed",
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        icon="mdi:speedometer",
        value_fn=lambda d: d.get("speed"),
    ),
    MovistarCarSensorDescription(
        key="odometer",
        translation_key="odometer",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        icon="mdi:counter",
        value_fn=lambda d: d.get("kilometers"),
    ),
    MovistarCarSensorDescription(
        key="trip_odometer",
        translation_key="trip_odometer",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        icon="mdi:map-marker-distance",
        value_fn=lambda d: d.get("total_kilometers"),
    ),
    MovistarCarSensorDescription(
        key="heading",
        translation_key="heading",
        icon="mdi:compass",
        native_unit_of_measurement="\u00b0",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("heading"),
    ),
    MovistarCarSensorDescription(
        key="last_reception",
        translation_key="last_reception",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-outline",
        value_fn=lambda d: _ms_to_datetime(d.get("last_reception")),
    ),
    MovistarCarSensorDescription(
        key="location_time",
        translation_key="location_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:map-clock",
        value_fn=lambda d: _ms_to_datetime(d.get("location_time")),
    ),
    MovistarCarSensorDescription(
        key="data_synced",
        translation_key="data_synced",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:sync",
        value_fn=lambda d: _ms_to_datetime(d.get("data_synced")),
    ),
    MovistarCarSensorDescription(
        key="wifi_ssid",
        translation_key="wifi_ssid",
        icon="mdi:wifi",
        value_fn=lambda d: d.get("wifi_ssid"),
    ),
    MovistarCarSensorDescription(
        key="wifi_data_used",
        translation_key="wifi_data_used",
        icon="mdi:wifi-arrow-up-down",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        suggested_display_precision=1,
        value_fn=lambda d: d.get("wifi_pack_used_mb"),
    ),
    MovistarCarSensorDescription(
        key="wifi_password",
        translation_key="wifi_password",
        icon="mdi:wifi-lock",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("wifi_password"),
    ),
    MovistarCarSensorDescription(
        key="wifi_data_pack_size",
        translation_key="wifi_data_pack_size",
        icon="mdi:database",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        value_fn=lambda d: d.get("wifi_pack_size_mb"),
    ),
    MovistarCarSensorDescription(
        key="wifi_ip_address",
        translation_key="wifi_ip_address",
        icon="mdi:ip-network",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("wifi_ip_address"),
    ),
    MovistarCarSensorDescription(
        key="battery_level",
        translation_key="battery_level",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:battery",
        value_fn=lambda d: d.get("battery_level"),
    ),
    MovistarCarSensorDescription(
        key="activation_date",
        translation_key="activation_date",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:calendar-check",
        entity_registry_enabled_default=False,
        value_fn=lambda d: _ms_to_datetime(d.get("activation_date")),
    ),
    MovistarCarSensorDescription(
        key="association_date",
        translation_key="association_date",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:calendar-link",
        entity_registry_enabled_default=False,
        value_fn=lambda d: _ms_to_datetime(d.get("association_date")),
    ),
    MovistarCarSensorDescription(
        key="disconnection_date",
        translation_key="disconnection_date",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:calendar-remove",
        entity_registry_enabled_default=False,
        value_fn=lambda d: _ms_to_datetime(d.get("disconnection_date")),
    ),
    MovistarCarSensorDescription(
        key="parking_status",
        translation_key="parking_status",
        icon="mdi:parking",
        value_fn=lambda d: d.get("parking_status"),
    ),
    MovistarCarSensorDescription(
        key="error_count",
        translation_key="error_count",
        icon="mdi:alert-circle",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("error_count"),
    ),
    MovistarCarSensorDescription(
        key="event_type",
        translation_key="event_type",
        icon="mdi:message-alert",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("event_type"),
    ),
    MovistarCarSensorDescription(
        key="sim_number",
        translation_key="sim_number",
        icon="mdi:sim",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("sim_number"),
    ),
    MovistarCarSensorDescription(
        key="latitude",
        translation_key="latitude",
        icon="mdi:latitude",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="°",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("latitude"),
    ),
    MovistarCarSensorDescription(
        key="longitude",
        translation_key="longitude",
        icon="mdi:longitude",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="°",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("longitude"),
    ),
    MovistarCarSensorDescription(
        key="wifi_pack_expiry",
        translation_key="wifi_pack_expiry",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:calendar-clock",
        value_fn=lambda d: _ms_to_datetime(d.get("wifi_pack_expiry")),
    ),
    MovistarCarSensorDescription(
        key="driving_score_daily",
        translation_key="driving_score_daily",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:steering",
        value_fn=lambda d: d.get("scoring_daily"),
    ),
    MovistarCarSensorDescription(
        key="driving_score_month",
        translation_key="driving_score_month",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:steering",
        value_fn=_score_month,
        attrs_fn=lambda d: _score_history(d),
    ),
    MovistarCarSensorDescription(
        key="next_itv",
        translation_key="next_itv",
        device_class=SensorDeviceClass.DATE,
        icon="mdi:car-wrench",
        value_fn=lambda d: _ms_to_date(d.get("next_itv_date")),
    ),
    MovistarCarSensorDescription(
        key="itv_days_left",
        translation_key="itv_days_left",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="d",
        icon="mdi:calendar-alert",
        value_fn=_itv_days_left,
    ),
    MovistarCarSensorDescription(
        key="avg_consumption",
        translation_key="avg_consumption",
        native_unit_of_measurement="L/100 km",
        icon="mdi:fuel",
        value_fn=lambda d: d.get("avg_consumption"),
    ),
    MovistarCarSensorDescription(
        key="fuel_liters",
        translation_key="fuel_liters",
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        icon="mdi:gas-station",
        value_fn=lambda d: d.get("fuel_liters"),
    ),
    MovistarCarSensorDescription(
        key="range_estimate",
        translation_key="range_estimate",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        icon="mdi:map-marker-distance",
        value_fn=lambda d: d.get("range_estimate"),
    ),
    MovistarCarSensorDescription(
        key="alarm_date",
        translation_key="alarm_date",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:alarm-light",
        entity_registry_enabled_default=False,
        value_fn=lambda d: _ms_to_datetime(d.get("alarm_date")),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MovistarCarCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        MovistarCarSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class MovistarCarSensor(CoordinatorEntity[MovistarCarCoordinator], SensorEntity):
    _attr_has_entity_name = True
    entity_description: MovistarCarSensorDescription

    def __init__(
        self,
        coordinator: MovistarCarCoordinator,
        description: MovistarCarSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{DOMAIN}_{coordinator.device_id}_{description.key}"
        )
        self._attr_device_info = coordinator.device_info

    @property
    def extra_state_attributes(self):
        fn = self.entity_description.attrs_fn
        if fn is None or self.coordinator.data is None:
            return None
        return fn(self.coordinator.data.data)

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data.data)
