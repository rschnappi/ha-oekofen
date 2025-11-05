"""Constants for the Ofen integration."""

DOMAIN = "ofen"
NAME = "Ofen"
VERSION = "1.0.0"

# Configuration and options
CONF_URL = "url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_LANGUAGE = "language"
CONF_INTERVAL = "interval"
CONF_DEBUG_MODE = "debug_mode"

# Defaults
DEFAULT_URL = "http://172.21.9.50"
DEFAULT_USERNAME = ""
DEFAULT_PASSWORD = ""
DEFAULT_LANGUAGE = "en"
DEFAULT_INTERVAL = 30
DEFAULT_DEBUG_MODE = False
DEFAULT_NAME = "Ofen Device"

# Language options
LANGUAGE_OPTIONS = ["de", "en"]

# Device classes
DEVICE_CLASS_TEMPERATURE = "temperature"
DEVICE_CLASS_SWITCH = "switch"