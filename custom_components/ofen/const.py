"""Constants for the ÖkOfen integration."""

DOMAIN = "ofen"
NAME = "ÖkOfen"
VERSION = "1.8.2"

# Configuration and options
CONF_URL = "url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_LANGUAGE = "language"
CONF_INTERVAL = "interval"
CONF_DEBUG_MODE = "debug_mode"
CONF_DEVICE_NAME = "device_name"

# Defaults
DEFAULT_URL = "172.21.9.50"
DEFAULT_USERNAME = ""
DEFAULT_PASSWORD = ""
DEFAULT_LANGUAGE = "en"
DEFAULT_INTERVAL = 30
DEFAULT_DEBUG_MODE = False
DEFAULT_NAME = "ÖkOfen Device"
DEFAULT_DEVICE_NAME = "ÖkOfen"

# Language options
LANGUAGE_OPTIONS = ["de", "en"]

# Device classes
DEVICE_CLASS_TEMPERATURE = "temperature"
DEVICE_CLASS_SWITCH = "switch"