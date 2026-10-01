"""Constants for the Napper integration."""

DOMAIN = "napper"
DEFAULT_NAME = "Napper"

# API Configuration
API_BASE_URL = "https://api.napper.app"

# Authentication Endpoints
AUTH_SEND_OTP = "/auth/send-otp"
AUTH_EMAIL_LOGIN = "/auth/email-login"
AUTH_REFRESH_TOKEN = "/auth/refresh-token"

# Data Endpoints
ENDPOINT_WIDGET_TODAY = "/widget-today"
ENDPOINT_LOGS = "/logs"
ENDPOINT_BABIES = "/babies"

# Polling interval in seconds
UPDATE_INTERVAL = 60

# Log categories
LOG_CATEGORY_NAP = "NAP"
LOG_CATEGORY_CHANGED_DIAPER = "CHANGED_DIAPER"
LOG_CATEGORY_SOLIDS = "SOLIDS"
LOG_CATEGORY_BED_TIME = "BED_TIME"
LOG_CATEGORY_WOKE_UP = "WOKE_UP"
LOG_CATEGORY_NURSING = "NURSING"
LOG_CATEGORY_NIGHT_WAKING = "NIGHT_WAKING"
LOG_CATEGORY_TEMPERATURE = "TEMPERATURE"
LOG_CATEGORY_MEDICINE = "MEDICINE"

# Diaper content types
DIAPER_WET = "WET"
DIAPER_MIXED = "MIXED"
DIAPER_POOP = "POOP"

# Config entry keys
CONF_BABY_ID = "baby_id"
CONF_BABY_NAME = "baby_name"
CONF_USER_ID = "user_id"
CONF_EMAIL = "email"
CONF_TOKEN = "token"
CONF_ID_TOKEN = "id_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_TOKEN_EXPIRY = "token_expiry"
CONF_DEVICE_ID = "device_id"
CONF_OTP = "otp"

# OAuth/OTP Flow State
FLOW_STATE_EMAIL = "email"
FLOW_STATE_OTP = "otp"
FLOW_STATE_BABY = "baby"
