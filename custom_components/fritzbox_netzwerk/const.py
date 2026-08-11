"""Konstanten der Integration fritzbox_netzwerk."""

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "fritzbox_netzwerk"
MANUFACTURER: Final = "FRITZ!"
VERSION: Final = "1.0.0"

PLATFORMS: Final = [Platform.SENSOR]

# --- Konfiguration (Config Entry) ---------------------------------------
CONF_USE_TLS: Final = "use_tls"

DEFAULT_HOST: Final = "fritz.box"
DEFAULT_USERNAME: Final = "admin"
DEFAULT_USE_TLS: Final = False

# --- Optionen (Options Flow) --------------------------------------------
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_TRACK_ADDRESS_SOURCE: Final = "track_address_source"
CONF_ADDRESS_SOURCE_INTERVAL: Final = "address_source_interval"

DEFAULT_SCAN_INTERVAL: Final = 60  # Sekunden
DEFAULT_TRACK_ADDRESS_SOURCE: Final = True
DEFAULT_ADDRESS_SOURCE_INTERVAL: Final = 15  # Minuten

MIN_SCAN_INTERVAL: Final = 15
MAX_SCAN_INTERVAL: Final = 3600

# --- Attribute des Sammelsensors ----------------------------------------
ATTR_HOSTS: Final = "hosts"
ATTR_TOTAL: Final = "gesamt"
ATTR_ACTIVE: Final = "aktiv"
ATTR_INACTIVE: Final = "inaktiv"
ATTR_GUESTS: Final = "gastnetz"
ATTR_BLOCKED: Final = "gesperrt"
ATTR_UPDATES: Final = "updates_verfuegbar"
ATTR_STATIC: Final = "statische_ip"
ATTR_LAST_SCAN: Final = "letzte_abfrage"
ATTR_ADDRESS_SOURCE_SCAN: Final = "letzte_ip_typ_abfrage"
ATTR_ADDRESS_SOURCE_STATE: Final = "ip_typ_erfassung"

# --- Dienste -------------------------------------------------------------
SERVICE_SET_DEVICE_NAME: Final = "set_device_name"
SERVICE_WAKE_ON_LAN: Final = "wake_on_lan"

ATTR_MAC: Final = "mac"
ATTR_NAME: Final = "name"

# --- Dashboard-Karte -----------------------------------------------------
CARD_FILENAME: Final = "fritzbox-netzwerk-card.js"
URL_BASE: Final = f"/{DOMAIN}"
CARD_URL: Final = f"{URL_BASE}/{CARD_FILENAME}"
