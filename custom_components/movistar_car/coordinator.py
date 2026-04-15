import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    MovistarCarAPI,
    MovistarCarAuthError,
    MovistarCarConnectionError,
)
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
)

_LOGGER = logging.getLogger(__name__)

AUTH_RETRY_DELAY = timedelta(minutes=10)
AUTH_MAX_RETRIES = 2


@dataclass
class MovistarCarData:
    vehicle_name: str
    device_id: int
    serial: str
    data: dict


class MovistarCarCoordinator(DataUpdateCoordinator[MovistarCarData]):
    config_entry: ConfigEntry

    def __init__(self, hass, config_entry: ConfigEntry) -> None:
        self.vehicle_index: int = config_entry.data.get(CONF_VEHICLE_INDEX, 0)
        self.service_id: int = config_entry.data.get(CONF_SERVICE_ID, 0)
        self.device_id: int = config_entry.data.get(CONF_DEVICE_ID, 0)
        self.vehicle_name: str = config_entry.data.get(CONF_VEHICLE_NAME, "Movistar Car")
        self.serial: str = config_entry.data.get("serial", "")

        poll_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            update_interval=timedelta(seconds=poll_interval),
            config_entry=config_entry,
        )

        self.api = MovistarCarAPI(
            username=config_entry.data[CONF_USERNAME],
            password=config_entry.data[CONF_PASSWORD],
            enterprise_key=config_entry.data.get(
                CONF_ENTERPRISE_KEY, DEFAULT_ENTERPRISE_KEY
            ),
        )

        token = config_entry.data.get(CONF_TOKEN)
        if token:
            self.api.set_token(token)

        self._auth_retry_count: int = 0
        self._next_auth_retry_at: datetime | None = None

    async def _async_update_data(self) -> MovistarCarData:
        if (
            self._next_auth_retry_at is not None
            and dt_util.utcnow() < self._next_auth_retry_at
        ):
            raise UpdateFailed(
                f"Waiting for auth retry at {self._next_auth_retry_at.isoformat()}"
            )

        try:
            data = await self.hass.async_add_executor_job(
                self.api.get_all_data, self.vehicle_index, self.service_id
            )
        except MovistarCarAuthError:
            # Try full re-login once using stored credentials
            try:
                self.api.token = None
                data = await self.hass.async_add_executor_job(
                    self.api.get_all_data, self.vehicle_index, self.service_id
                )
            except MovistarCarAuthError as retry_err:
                self._auth_retry_count += 1
                if self._auth_retry_count > AUTH_MAX_RETRIES:
                    self._auth_retry_count = 0
                    self._next_auth_retry_at = None
                    raise ConfigEntryAuthFailed(
                        f"Authentication failed after {AUTH_MAX_RETRIES} retries. "
                        "Please reconfigure."
                    ) from retry_err
                self._next_auth_retry_at = dt_util.utcnow() + AUTH_RETRY_DELAY
                raise UpdateFailed(
                    f"Auth re-login failed, retry {self._auth_retry_count}/"
                    f"{AUTH_MAX_RETRIES} at {self._next_auth_retry_at.isoformat()}"
                ) from retry_err
            except Exception as retry_err:
                raise UpdateFailed(f"Re-login failed: {retry_err}") from retry_err
        except MovistarCarConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

        # Successful fetch — clear any pending auth retry state
        self._auth_retry_count = 0
        self._next_auth_retry_at = None

        # Persist refreshed token
        if self.api.token and self.api.token != self.config_entry.data.get(CONF_TOKEN):
            new_data = {**self.config_entry.data, CONF_TOKEN: self.api.token}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )

        return MovistarCarData(
            vehicle_name=self.vehicle_name,
            device_id=self.device_id,
            serial=self.serial,
            data=data,
        )
