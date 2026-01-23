"""Constants for the Norway Seaforecast integration."""

DOMAIN = "norway_seaforecast"

# Config entry fields
CONF_LONGITUDE = "longitude"
CONF_LATITUDE = "latitude"
CONF_DEPTH = "depth"
CONF_SENSOR_NAME = "sensor_name"
CONF_VARIABLES = "variables"

# Default values
DEFAULT_DEPTH = 0
DEFAULT_SENSOR_NAME = "Sea Temperature"
DEFAULT_VARIABLES = ["temperature"]

# Update interval
UPDATE_INTERVAL = 600  # 10 minutes in seconds

# API endpoints
API_BASE_URL = "https://api.havvarsel.no/apis/duapi/havvarsel/v2/"
API_PROJECTION_URL = f"{API_BASE_URL}dataprojection"
API_VARIABLES_URL = f"{API_BASE_URL}variables"
API_DATAPROJECTION_VARIABLES_URL = f"{API_BASE_URL}dataprojectionvariables"
