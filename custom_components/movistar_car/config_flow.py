import logging

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import callback

from .api import MovistarCarAPI, MovistarCarAuthError, MovistarCarConnectionError
from .const import (
    CONF_DEVICE_ID,
    CONF_ENTERPRISE_KEY,
    CONF_SERVICE_ID,
    CONF_TOKEN,
    CONF_VEHICLE_INDEX,
    CONF_VEHICLE_NAME,
    DEFAULT_ENTERPRISE_KEY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(
            CONF_ENTERPRISE_KEY, default=DEFAULT_ENTERPRISE_KEY
        ): str,
    }
)


class MovistarCarConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._api: MovistarCarAPI | None = None
        self._devices: list[dict] = []
        self._location_data: list[dict] = []
        self._username: str = ""
        self._password: str = ""
        self._enterprise_key: str = ""
        self._token: str = ""

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        errors = {}

        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]
            self._enterprise_key = user_input.get(
                CONF_ENTERPRISE_KEY, DEFAULT_ENTERPRISE_KEY
            )

            self._api = MovistarCarAPI(
                self._username, self._password, self._enterprise_key
            )

            try:
                session_data = await self.hass.async_add_executor_job(
                    self._api.login
                )
            except MovistarCarAuthError:
                errors["base"] = "invalid_auth"
            except MovistarCarConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during login")
                errors["base"] = "unknown"
            else:
                self._token = self._api.token
                self._devices = session_data.get("Devices", [])

                if not self._devices:
                    errors["base"] = "no_devices"
                else:
                    # Fetch location data to get ServiceIds
                    try:
                        for i in range(len(self._devices)):
                            loc = await self.hass.async_add_executor_job(
                                self._api.get_location, i
                            )
                            self._location_data.append(loc)
                    except Exception:
                        _LOGGER.warning("Could not fetch location data")

                    if len(self._devices) == 1:
                        return await self._create_entry(0)

                    return await self.async_step_select_vehicle()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_select_vehicle(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            index = int(user_input[CONF_VEHICLE_INDEX])
            return await self._create_entry(index)

        vehicle_options = {}
        for i, device in enumerate(self._devices):
            name = device.get("WiFiStatus", {}).get("SSID", f"Vehicle {i + 1}")
            serial = device.get("Serial", "")
            label = f"{name} ({serial})" if serial else name
            vehicle_options[str(i)] = label

        return self.async_show_form(
            step_id="select_vehicle",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_VEHICLE_INDEX): vol.In(vehicle_options),
                }
            ),
        )

    async def _create_entry(self, vehicle_index: int) -> ConfigFlowResult:
        device = self._devices[vehicle_index]
        device_id = device.get("Id", 0)
        serial = device.get("Serial", "")
        vehicle_name = device.get("WiFiStatus", {}).get(
            "SSID", f"Vehicle {vehicle_index + 1}"
        )

        # Get ServiceId from location data
        service_id = 0
        if vehicle_index < len(self._location_data):
            status_list = self._location_data[vehicle_index].get("Status", [])
            if status_list:
                service_id = status_list[0].get("ServiceId", 0)

        unique_id = f"{self._username}_{device_id}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=vehicle_name,
            data={
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_ENTERPRISE_KEY: self._enterprise_key,
                CONF_TOKEN: self._token,
                CONF_VEHICLE_INDEX: vehicle_index,
                CONF_DEVICE_ID: device_id,
                CONF_SERVICE_ID: service_id,
                CONF_VEHICLE_NAME: vehicle_name,
                "serial": serial,
            },
        )

    async def async_step_reauth(
        self, entry_data: dict
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        errors = {}

        if user_input is not None:
            api = MovistarCarAPI(
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                user_input.get(CONF_ENTERPRISE_KEY, DEFAULT_ENTERPRISE_KEY),
            )
            try:
                await self.hass.async_add_executor_job(api.login)
            except MovistarCarAuthError:
                errors["base"] = "invalid_auth"
            except MovistarCarConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                entry = self.hass.config_entries.async_get_entry(
                    self.context["entry_id"]
                )
                if entry:
                    new_data = {
                        **entry.data,
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_TOKEN: api.token,
                    }
                    if CONF_ENTERPRISE_KEY in user_input:
                        new_data[CONF_ENTERPRISE_KEY] = user_input[
                            CONF_ENTERPRISE_KEY
                        ]
                    self.hass.config_entries.async_update_entry(
                        entry, data=new_data
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MovistarCarOptionsFlow()


class MovistarCarOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=current_interval
                    ): vol.All(
                        vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=3600)
                    ),
                }
            ),
        )
