DOMAIN = "movistar_car"

API_BASE_URL = "https://api-xmp-cli.net4things.com/API/v3"
API_SESSION_URL = f"{API_BASE_URL}/session"
API_LOCATION_URL = f"{API_BASE_URL}/session/location-status"
API_OBD_CODES_URL = f"{API_BASE_URL}/obd-diagnostic-codes"

API_USER_AGENT = "MovistarMbility/34 CFNetwork/3826.500.111.2.2 Darwin/24.4.0"
DEFAULT_ENTERPRISE_KEY = "8d2e47e5-8ceb-c824-e216-cc68e9aad39c"

CONF_ENTERPRISE_KEY = "enterprise_key"
CONF_VEHICLE_INDEX = "vehicle_index"
CONF_DEVICE_ID = "device_id"
CONF_SERVICE_ID = "service_id"
CONF_VEHICLE_NAME = "vehicle_name"
CONF_TOKEN = "token"

DEFAULT_SCAN_INTERVAL = 120
MIN_SCAN_INTERVAL = 30
