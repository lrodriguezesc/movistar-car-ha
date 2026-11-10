"""Diagnostics for Movistar Car. Personal data is removed before download."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import CONF_ENTERPRISE_KEY, CONF_TOKEN, DOMAIN
from .coordinator import MovistarCarCoordinator

TO_REDACT = {
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_ENTERPRISE_KEY,
    "title",
    "unique_id",
    "vehicle_name",
    "serial",
    "device_id",
    "service_id",
    "wifi_ssid",
    "wifi_password",
    "wifi_ip_address",
    "sim_serial",
    "sim_number",
    "latitude",
    "longitude",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator: MovistarCarCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data.data if coordinator.data else {}

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval": str(coordinator.update_interval),
            "tank_capacity": coordinator.tank_capacity,
        },
        "consumption": {
            "window_km": coordinator.consumption.window_km,
            "segments": len(coordinator.consumption.segments),
        },
        "data": async_redact_data(data, TO_REDACT),
    }
