"""Konstanten der Integration fritzbox_netzwerk."""

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "fritzbox_netzwerk"
MANUFACTURER: Final = "FRITZ!"
VERSION: Final = "1.6.3"

PLATFORMS: Final = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.EVENT,
]

# --- Konfiguration (Config Entry) ---------------------------------------
CONF_USE_TLS: Final = "use_tls"
CONF_PORT: Final = "port"
CONF_REMOTE_ACCESS: Final = "remote_access"

DEFAULT_HOST: Final = "fritz.box"
DEFAULT_USERNAME: Final = "admin"
DEFAULT_USE_TLS: Final = False
DEFAULT_PORT: Final = 0
DEFAULT_REMOTE_ACCESS: Final = False

# --- Optionen (Options Flow) --------------------------------------------
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_TRACK_ADDRESS_SOURCE: Final = "track_address_source"
CONF_ADDRESS_SOURCE_INTERVAL: Final = "address_source_interval"
CONF_TRACK_WLAN_BAND: Final = "track_wlan_band"
CONF_ENABLE_DEVICE_TRACKER: Final = "enable_device_tracker"
CONF_ENABLE_CONTROLS: Final = "enable_controls"
CONF_ENABLE_REPEATERS: Final = "enable_repeaters"
CONF_PAIRING_MINUTES: Final = "pairing_minutes"
# Benannte IP-Bereiche fuer Zaehler-Sensoren (Idee 7 aus feature-ideen.md),
# z. B. "Drucker=192.168.2.*" - eine Zeile je Bereich, siehe hosts.parse_ip_ranges.
CONF_IP_RANGES: Final = "ip_ranges"

DEFAULT_SCAN_INTERVAL: Final = 60  # Sekunden
DEFAULT_TRACK_ADDRESS_SOURCE: Final = True
DEFAULT_ADDRESS_SOURCE_INTERVAL: Final = 15  # Minuten
DEFAULT_TRACK_WLAN_BAND: Final = True
DEFAULT_ENABLE_DEVICE_TRACKER: Final = False
DEFAULT_ENABLE_CONTROLS: Final = False
DEFAULT_ENABLE_REPEATERS: Final = True
DEFAULT_PAIRING_MINUTES: Final = 5  # Minuten
DEFAULT_IP_RANGES: Final = ""

MIN_PAIRING_MINUTES: Final = 1
MAX_PAIRING_MINUTES: Final = 120

# Laut AVMs TR-064-Beschreibung des Hosts-Dienstes (X_AVM-DE_GetInfo /
# X_AVM-DE_FriendlynameMaxChars): die FRITZ!Box erlaubt fuer die
# "Bezeichnung" (X_AVM-DE_FriendlyName) 1 bis 64 Zeichen.
MAX_FRIENDLY_NAME_LENGTH: Final = 64
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
SERVICE_SET_INTERNET_ACCESS: Final = "set_internet_access"
SERVICE_SET_MAC_FILTER: Final = "set_mac_filter"
SERVICE_START_PAIRING: Final = "start_pairing"
SERVICE_REBOOT_MESH: Final = "reboot_mesh"
SERVICE_GAST_WLAN_INFO: Final = "gast_wlan_info"

# WLANConfiguration-Dienstindex des Gast-WLANs - dieselbe Annahme (Dualband-
# Box: 1 = 2,4 GHz, 2 = 5 GHz, 3 = Gast), die switch.py (WLAN_BANDS) und
# coordinator.py (_wlan_supported) bereits fuer den Gast-WLAN-Schalter
# verwenden. Bewusst NICHT fritzconnections eigene FritzGuestWLAN-
# Autoerkennung (waehlt den hoechsten vorhandenen WLANConfiguration-Index) -
# auf Boxen mit mehr als drei WLAN-Diensten wuerde das vom Schalter abweichen
# und zu widerspruechlichen Angaben zwischen Schalter und Gast-WLAN-Info
# fuehren (Idee 11 aus feature-ideen.md).
GAST_WLAN_SERVICE_INDEX: Final = 3

ATTR_MAC: Final = "mac"
ATTR_NAME: Final = "name"
ATTR_BLOCKED_PARAM: Final = "blocked"
ATTR_ENABLED: Final = "enabled"
ATTR_MINUTES: Final = "minutes"
# Optionales Feld in allen Diensten (Idee 14 aus feature-ideen.md): ohne
# Angabe wirkt ein Dienst weiterhin auf die zuerst geladene Box (bisheriges
# Verhalten, siehe README "Bekannte Einschränkungen").
ATTR_CONFIG_ENTRY: Final = "config_entry"

# --- Speicher ------------------------------------------------------------
LAST_SEEN_STORAGE_VERSION: Final = 1
FIRST_SEEN_STORAGE_VERSION: Final = 1
PAIRING_STORAGE_VERSION: Final = 1

# Filter "Neu (letzte N Tage)" in der Karte (Idee 2 aus feature-ideen.md).
NEW_DEVICE_FILTER_DAYS: Final = 7

# DHCP-Bereich (Idee 8 aus feature-ideen.md): Anfang/Ende aendern sich in der
# Praxis so gut wie nie (nur bei manueller Umstellung der DHCP-Einstellungen
# an der Box) - deshalb reicht ein fester, grosszuegiger Abstand zwischen den
# Abfragen von ``LANHostConfigManagement1.GetInfo``, unabhaengig von der
# (fuer etwas anderes gedachten) IP-Typ-Erfassung.
DHCP_POOL_INTERVAL_MINUTES: Final = 30

# --- Dashboard-Karte -----------------------------------------------------
CARD_FILENAME: Final = "fritzbox-netzwerk-card.js"
URL_BASE: Final = f"/{DOMAIN}"
CARD_URL: Final = f"{URL_BASE}/{CARD_FILENAME}"
