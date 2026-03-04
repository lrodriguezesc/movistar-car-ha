import logging
from datetime import datetime, timezone

import requests

from .const import (
    API_LOCATION_URL,
    API_OBD_CODES_URL,
    API_SESSION_URL,
    API_USER_AGENT,
    DEFAULT_ENTERPRISE_KEY,
)

_LOGGER = logging.getLogger(__name__)


class MovistarCarAuthError(Exception):
    pass


class MovistarCarConnectionError(Exception):
    pass


class MovistarCarAPIError(Exception):
    pass


class MovistarCarAPI:
    def __init__(self, username: str, password: str, enterprise_key: str | None = None):
        self.username = username
        self.password = password
        self.enterprise_key = enterprise_key or DEFAULT_ENTERPRISE_KEY
        self.token: str | None = None
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": API_USER_AGENT,
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "plain/text,application/json",
            }
        )

    def set_token(self, token: str) -> None:
        self.token = token

    def login(self) -> dict:
        """Full login with credentials. Returns session data."""
        payload = {
            "Username": self.username,
            "Password": self.password,
            "EnterpriseKey": self.enterprise_key,
        }
        try:
            r = self.session.put(API_SESSION_URL, json=payload)
        except requests.RequestException as err:
            raise MovistarCarConnectionError(f"Connection failed: {err}") from err

        if r.status_code != 200:
            raise MovistarCarAuthError(f"Login failed with status {r.status_code}")

        data = r.json()
        self.token = data.get("Token")
        if not self.token:
            raise MovistarCarAuthError("No token in login response")

        return data.get("Data", data)

    def validate_token(self) -> dict | None:
        """Validate existing token. Returns session data or None if invalid."""
        if not self.token:
            return None

        try:
            r = self.session.get(
                API_SESSION_URL, headers={"Token": self.token}
            )
        except requests.RequestException:
            return None

        if r.status_code != 200:
            return None

        return r.json()

    def authenticate(self) -> dict:
        """Try stored token first, fall back to login. Returns session data."""
        if self.token:
            data = self.validate_token()
            if data is not None:
                return data

        return self.login()

    def get_devices(self) -> list[dict]:
        """Authenticate and return devices list."""
        data = self.authenticate()
        devices = data.get("Devices", [])
        if not devices:
            _LOGGER.warning("No devices found in API response")
        return devices

    def get_location(self, vehicle_index: int = 0) -> dict:
        """Fetch location status for a vehicle."""
        if not self.token:
            raise MovistarCarAuthError("Not authenticated")

        url = f"{API_LOCATION_URL}/{vehicle_index}"
        try:
            r = self.session.get(url, headers={"Token": self.token})
        except requests.RequestException as err:
            raise MovistarCarConnectionError(f"Connection failed: {err}") from err

        if r.status_code == 401:
            raise MovistarCarAuthError("Token expired")

        if r.status_code != 200:
            raise MovistarCarAPIError(f"Location request failed: {r.status_code}")

        return r.json()

    def get_obd_codes(self, service_id: int) -> list:
        """Fetch OBD diagnostic codes for a service."""
        if not self.token:
            raise MovistarCarAuthError("Not authenticated")

        url = f"{API_OBD_CODES_URL}/{service_id}/query"
        try:
            r = self.session.post(url, headers={"Token": self.token})
        except requests.RequestException as err:
            raise MovistarCarConnectionError(f"Connection failed: {err}") from err

        if r.status_code == 401:
            raise MovistarCarAuthError("Token expired")

        if r.status_code == 404:
            return []

        if r.status_code != 200:
            _LOGGER.warning("OBD codes request failed: %s", r.status_code)
            return []

        data = r.json()
        return data if isinstance(data, list) else []

    def get_all_data(self, vehicle_index: int, service_id: int) -> dict:
        """Fetch all vehicle data. Returns combined dict."""
        session_data = self.authenticate()

        devices = session_data.get("Devices", [])
        device = devices[vehicle_index] if vehicle_index < len(devices) else {}

        location_data = self.get_location(vehicle_index)
        status_list = location_data.get("Status", [])
        status = status_list[0] if status_list else {}
        latest_event = status.get("LatestEvent", {})

        obd_codes = self.get_obd_codes(service_id)
        has_errors = any(not code.get("Solved", True) for code in obd_codes)

        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

        wifi = device.get("WiFiStatus", {})

        return {
            # Device data
            "device_id": device.get("Id"),
            "serial": device.get("Serial"),
            "voltage": device.get("Voltage"),
            "connected": device.get("Connected", False),
            "kilometers": device.get("Kilometers"),
            "last_reception": device.get("LastReception"),
            "device_status": device.get("DeviceStatus"),
            "activation_date": device.get("ActivationDate"),
            "association_date": device.get("AssociationDate"),
            "battery_level": device.get("BatteryLevel"),
            "incompatible": device.get("Incompatible", False),
            "disconnection_date": device.get("DisconnectionDate"),
            # WiFi data
            "wifi_enabled": wifi.get("Enabled"),
            "wifi_ssid": wifi.get("SSID"),
            "wifi_password": wifi.get("Password"),
            "wifi_data_used": wifi.get("UsedData"),
            "wifi_data_pack_size": wifi.get("DataPackSize"),
            "wifi_ip_address": wifi.get("IPAddress"),
            # SIM data
            "sim_serial": device.get("SIMSerial"),
            "sim_number": device.get("SIMNumber"),
            # Location data
            "service_id": status.get("ServiceId"),
            "latitude": latest_event.get("Latitude"),
            "longitude": latest_event.get("Longitude"),
            "speed": latest_event.get("Speed"),
            "fuel": latest_event.get("Fuel"),
            "heading": latest_event.get("Heading"),
            "valid_position": latest_event.get("ValidPosition", False),
            "location_time": latest_event.get("Date"),
            "total_kilometers": status.get("TotalKilometers"),
            "event_type": latest_event.get("EventType"),
            "parking_status": status.get("OnStreetParkingStatus"),
            # OBD data
            "errors": has_errors,
            "error_count": sum(1 for c in obd_codes if not c.get("Solved", True)),
            "obd_codes": obd_codes,
            # Derived
            "moving": (latest_event.get("Speed") or 0) > 0,
            # Meta
            "data_synced": now_ms,
        }
