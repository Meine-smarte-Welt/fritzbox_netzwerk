"""Die Integration fritzbox_netzwerk."""

from __future__ import annotations

import base64
import logging
import os
from collections.abc import Mapping
from typing import Any, Final

import voluptuous as vol
from fritzconnection.core.exceptions import (
    FritzAuthorizationError,
    FritzConnectionException,
    FritzSecurityError,
    FritzServiceError,
)
from fritzconnection.lib.fritzhosts import FritzHosts
from fritzconnection.lib.fritzwlan import FritzWLAN
from requests.exceptions import ConnectionError as RequestsConnectionError

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir

from .auth_guard import AUTH_FAILURE_LIMIT, AuthFailureGuard
from .connection import create_connection
from .const import (
    ATTR_BLOCKED_PARAM,
    ATTR_CONFIG_ENTRY,
    ATTR_ENABLED,
    ATTR_LABEL,
    ATTR_MAC,
    ATTR_MINUTES,
    ATTR_NAME,
    ATTR_NOTE,
    ATTR_OVERWRITE,
    ATTR_PROFILE,
    ATTR_RESERVED,
    CARD_FILENAME,
    CARD_URL,
    CONF_REMOTE_ACCESS,
    DOMAIN,
    GAST_WLAN_SERVICE_INDEX,
    MANUFACTURER,
    MAX_FRIENDLY_NAME_LENGTH,
    MAX_PAIRING_MINUTES,
    MIN_PAIRING_MINUTES,
    PLATFORMS,
    SERVICE_GAST_WLAN_INFO,
    SERVICE_INSTALL_BLUEPRINTS,
    SERVICE_GET_ACCESS_PROFILE,
    SERVICE_LIST_ACCESS_PROFILES,
    SERVICE_SET_ACCESS_PROFILE,
    SERVICE_REBOOT_MESH,
    SERVICE_SET_DEVICE_NAME,
    SERVICE_SET_DEVICE_NOTE,
    SERVICE_SET_INTERNET_ACCESS,
    SERVICE_SET_MAC_FILTER,
    SERVICE_START_PAIRING,
    SERVICE_UPDATE_OUI,
    SERVICE_WAKE_ON_LAN,
    URL_BASE,
    VERSION,
)
from .coordinator import FritzboxNetzwerkCoordinator
from .hosts import normalize_mac

# Beacontype -> "offenes Netz, kein Passwort noetig". Gespiegelt aus
# fritzconnection.lib.fritzwlan._BEACONTYPE_TO_QR_SECURITY (Version 1.15.1,
# siehe requirements in manifest.json) - dort nicht als oeffentliche API
# gedacht (fuehrender Unterstrich), darum hier eine eigene, auf das fuer
# diese Integration Noetige reduzierte Kopie statt eines Imports einer
# privaten Fremd-Funktion.
_OPEN_BEACON_TYPES: Final = frozenset({"None", "OWE", "OWETrans"})

_LOGGER = logging.getLogger(__name__)

type FritzboxNetzwerkConfigEntry = ConfigEntry[FritzboxNetzwerkCoordinator]

MAC_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MAC): cv.string,
        vol.Optional(ATTR_NAME): cv.string,
        vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
    }
)

INTERNET_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MAC): cv.string,
        vol.Required(ATTR_BLOCKED_PARAM): cv.boolean,
        vol.Optional(ATTR_MINUTES): vol.All(vol.Coerce(int), vol.Range(min=1, max=10080)),
        vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
    }
)

MAC_FILTER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENABLED): cv.boolean,
        vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
    }
)

PAIRING_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_MINUTES): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_PAIRING_MINUTES, max=MAX_PAIRING_MINUTES)
        ),
        vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
    }
)

REBOOT_MESH_SCHEMA = vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY): cv.string})

GAST_WLAN_INFO_SCHEMA = vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY): cv.string})

# Nicht uebergebene Felder bleiben unveraendert; ein leerer Text loescht das Feld.
DEVICE_NOTE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MAC): cv.string,
        vol.Optional(ATTR_LABEL): cv.string,
        vol.Optional(ATTR_NOTE): cv.string,
        vol.Optional(ATTR_RESERVED): cv.boolean,
        vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
    }
)

UPDATE_OUI_SCHEMA = vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY): cv.string})

INSTALL_BLUEPRINTS_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_OVERWRITE, default=False): cv.boolean, vol.Optional(ATTR_CONFIG_ENTRY): cv.string}
)

LIST_PROFILES_SCHEMA = vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY): cv.string})

GET_PROFILE_SCHEMA = vol.Schema(
    {vol.Required(ATTR_MAC): cv.string, vol.Optional(ATTR_CONFIG_ENTRY): cv.string}
)

SET_PROFILE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MAC): cv.string,
        vol.Required(ATTR_PROFILE): cv.string,
        vol.Optional(ATTR_MINUTES): vol.All(vol.Coerce(int), vol.Range(min=1, max=10080)),
        vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
    }
)


async def async_setup_entry(
    hass: HomeAssistant, entry: FritzboxNetzwerkConfigEntry
) -> bool:
    """Richtet einen Konfigurationseintrag ein."""

    def _connect() -> FritzHosts:
        connection = create_connection(entry.data)
        return FritzHosts(fc=connection)

    # Ein Zaehler je Home-Assistant-Lauf: ueberlebt die Wiederholungen beim
    # Start, damit eine kurzzeitig ablehnende Box nicht sofort die erneute
    # Anmeldung ausloest (siehe auth_guard.py).
    guard: AuthFailureGuard = hass.data.setdefault(f"{DOMAIN}_auth_guard", AuthFailureGuard())

    try:
        fritz_hosts = await hass.async_add_executor_job(_connect)
    except (FritzSecurityError, FritzAuthorizationError) as err:
        count, give_up = guard.failure(entry.entry_id)
        if give_up:
            raise ConfigEntryAuthFailed(str(err)) from err
        raise ConfigEntryNotReady(
            f"FRITZ!Box hat die Anmeldung abgelehnt (Versuch {count} von "
            f"{AUTH_FAILURE_LIMIT}), neuer Versuch folgt: {err}"
        ) from err
    except (FritzConnectionException, RequestsConnectionError) as err:
        raise ConfigEntryNotReady(
            f"FRITZ!Box unter {entry.data[CONF_HOST]} nicht erreichbar: {err}"
        ) from err

    coordinator = FritzboxNetzwerkCoordinator(hass, entry, fritz_hosts, guard)
    await coordinator.async_load_last_seen()
    await coordinator.async_load_first_seen()
    await coordinator.async_load_notes()
    await coordinator.async_load_blocks()
    await coordinator.async_load_profile_reverts()
    await coordinator.async_load_oui()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    # Lief beim letzten Stopp ein Pairing (MAC-Filter zeitweise aus), wird es
    # hier fortgesetzt bzw. - bei abgelaufener Frist - sofort beendet.
    await coordinator.async_restore_pairing()
    entry.async_on_unload(coordinator.async_cancel_pairing_timer)

    # Das Hauptgeraet (die FRITZ!Box) schon vor den Plattformen anlegen: die
    # Repeater-Geraete haengen per ``via_device`` daran und brauchen es beim
    # Anlegen bereits in der Geraeteregistrierung.
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer=MANUFACTURER,
        name=entry.title,
    )

    await _async_register_card(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_register_services(hass)
    _async_update_remote_access_issue(hass, entry)

    # Kein add_update_listener: der Neuladen bei Options-Aenderungen wird von
    # OptionsFlowWithReload (siehe config_flow.py) uebernommen. Beides zusammen
    # loest seit einer aktuellen Home-Assistant-Version einen Fehler aus
    # ("update listeners should not be used with OptionsFlowWithReload").
    return True


def _remote_access_issue_id(entry: FritzboxNetzwerkConfigEntry) -> str:
    return f"remote_access_no_tls_verification_{entry.entry_id}"


def _async_update_remote_access_issue(
    hass: HomeAssistant, entry: FritzboxNetzwerkConfigEntry
) -> None:
    """Legt bei aktivem Fernzugriff einen Reparaturhinweis an (Idee 15).

    ``fritzconnection`` prueft TLS-Zertifikate grundsaetzlich nicht
    (``verify=False``, siehe README "Zugriff auf eine entfernte FRITZ!Box",
    seit 1.6.2). Im lokalen Heimnetz ein akzeptiertes, geringes Risiko - beim
    Fernzugriff ueber das offene Internet aber ein hoeheres (potenziell
    Man-in-the-Middle). Bisher stand das nur im README; seit 1.6.3 zusaetzlich
    als sichtbarer, nicht automatisch behebbarer Hinweis unter Einstellungen >
    Reparaturen, solange der Fernzugriff eingeschaltet ist. Wird bei jedem
    Setup neu bewertet, damit ein spaeteres Abschalten (Optionen/Reconfigure
    loesen beide einen Neuladen aus) den Hinweis automatisch wieder entfernt.
    """
    issue_id = _remote_access_issue_id(entry)
    if entry.data.get(CONF_REMOTE_ACCESS):
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="remote_access_no_tls_verification",
            translation_placeholders={"host": entry.data.get(CONF_HOST, "")},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, issue_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: FritzboxNetzwerkConfigEntry
) -> bool:
    """Entlaedt einen Konfigurationseintrag."""
    ir.async_delete_issue(hass, DOMAIN, _remote_access_issue_id(entry))
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded and not hass.config_entries.async_loaded_entries(DOMAIN):
        for service in (
            SERVICE_SET_DEVICE_NAME,
            SERVICE_WAKE_ON_LAN,
            SERVICE_SET_INTERNET_ACCESS,
            SERVICE_SET_MAC_FILTER,
            SERVICE_START_PAIRING,
            SERVICE_REBOOT_MESH,
            SERVICE_GAST_WLAN_INFO,
            SERVICE_SET_DEVICE_NOTE,
            SERVICE_UPDATE_OUI,
            SERVICE_LIST_ACCESS_PROFILES,
            SERVICE_GET_ACCESS_PROFILE,
            SERVICE_SET_ACCESS_PROFILE,
            SERVICE_INSTALL_BLUEPRINTS,
        ):
            hass.services.async_remove(DOMAIN, service)
    return unloaded


# ---------------------------------------------------------------------------
# Dashboard-Karte
# ---------------------------------------------------------------------------


async def _async_register_card(hass: HomeAssistant) -> None:
    """Stellt die Karten-Datei bereit und traegt sie als Ressource ein."""
    card_path = os.path.join(os.path.dirname(__file__), "www", CARD_FILENAME)
    if not os.path.exists(card_path):
        _LOGGER.warning("Karten-Datei %s nicht gefunden", card_path)
        return

    if URL_BASE not in hass.data.setdefault(f"{DOMAIN}_static_paths", set()):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    URL_BASE, os.path.join(os.path.dirname(__file__), "www"), False
                )
            ]
        )
        hass.data[f"{DOMAIN}_static_paths"].add(URL_BASE)

    await _async_ensure_lovelace_resource(hass)


async def _async_ensure_lovelace_resource(hass: HomeAssistant) -> None:
    """Traegt die Karte einmalig in die Lovelace-Ressourcen ein.

    Bewusst KEIN ``add_extra_js_url()`` zusaetzlich: ein Browser fuehrt
    eine Modul-URL nur einmal aus, ein doppelter Ladeweg laesst die Karte
    stumm scheitern. Ein vorhandener Eintrag wird aktualisiert statt
    dupliziert, damit der Versionsparameter den Browser-Cache umgeht.
    """
    versioned_url = f"{CARD_URL}?v={VERSION}"
    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        _LOGGER.debug("Lovelace noch nicht geladen, Ressource nicht eingetragen")
        return

    resources = getattr(lovelace, "resources", None)
    if resources is None and isinstance(lovelace, dict):
        resources = lovelace.get("resources")
    if resources is None:
        return

    # Im YAML-Modus verwaltet der Nutzer die Ressourcen selbst.
    if getattr(resources, "store", None) is None:
        _LOGGER.info(
            "Lovelace laeuft im YAML-Modus. Bitte '%s' manuell als Modul-Ressource "
            "eintragen",
            versioned_url,
        )
        return

    if not getattr(resources, "loaded", False):
        await resources.async_load()
        resources.loaded = True

    for item in resources.async_items():
        url = str(item.get("url", ""))
        if url.split("?")[0] != CARD_URL:
            continue
        if url != versioned_url:
            await resources.async_update_item(item["id"], {"url": versioned_url})
            _LOGGER.debug("Lovelace-Ressource auf %s aktualisiert", versioned_url)
        return

    await resources.async_create_item({"res_type": "module", "url": versioned_url})
    _LOGGER.debug("Lovelace-Ressource %s angelegt", versioned_url)


# ---------------------------------------------------------------------------
# Dienste
# ---------------------------------------------------------------------------


def _async_register_services(hass: HomeAssistant) -> None:
    """Meldet die Dienste an (einmalig, unabhaengig von der Anzahl der Boxen)."""

    def _resolve_coordinator(call_data: Mapping[str, Any]) -> FritzboxNetzwerkCoordinator:
        """Liefert die FRITZ!Box, auf die sich ein Dienstaufruf bezieht.

        Ohne das optionale Feld ``config_entry`` wirkt der Dienst wie bisher
        (vor 1.6.3) auf die zuerst geladene Box - das deckt weiterhin den
        Normalfall (eine Box) ab, ohne bestehende Automationen/Skripte zu
        brechen. Erst mit mehreren eingerichteten Boxen (Idee 14 aus
        feature-ideen.md) wird das Feld gebraucht, um gezielt eine davon
        anzusprechen.
        """
        entries = hass.config_entries.async_loaded_entries(DOMAIN)
        if not entries:
            raise HomeAssistantError("Keine eingerichtete FRITZ!Box gefunden")

        entry_id = call_data.get(ATTR_CONFIG_ENTRY)
        if not entry_id:
            return entries[0].runtime_data

        for entry in entries:
            if entry.entry_id == entry_id:
                return entry.runtime_data
        raise HomeAssistantError(
            f"Keine geladene FRITZ!Box mit config_entry '{entry_id}' gefunden. "
            "Zur Auswahl stehen: "
            + ", ".join(f"{entry.title} ({entry.entry_id})" for entry in entries)
        )

    async def _handle_set_device_name(call: ServiceCall) -> None:
        """Setzt die Bezeichnung (X_AVM-DE_FriendlyName) eines Geraets.

        Bewusst NICHT ``X_AVM-DE_SetHostNameByMACAddress`` (das setzt den
        technischen DNS-Hostnamen; laut AVMs TR-064-Beschreibung sind dort
        nur ASCII-Buchstaben und -Ziffern erlaubt - kein Leerzeichen, Punkt
        oder Sonderzeichen, sonst UPnPError 402 "Invalid Args"). Angezeigt
        wird in der Karte und in ``name_writeable`` ohnehin die
        ``X_AVM-DE_FriendlyName`` (siehe ``hosts.display_name()`` und
        ``X_AVM-DE_FriendlyNameIsWriteable``); dieser Dienst schreibt jetzt
        genau dorthin. Laut AVM 1-64 Zeichen, keine dokumentierte
        Zeichenbeschraenkung.
        """
        coordinator = _resolve_coordinator(call.data)
        mac = normalize_mac(call.data[ATTR_MAC])
        name = call.data.get(ATTR_NAME, "")
        if not name:
            raise HomeAssistantError("Es wurde kein neuer Name uebergeben")
        if len(name) > MAX_FRIENDLY_NAME_LENGTH:
            raise HomeAssistantError(
                f"Der Name ist zu lang ({len(name)} Zeichen) - die FRITZ!Box "
                f"erlaubt hoechstens {MAX_FRIENDLY_NAME_LENGTH} Zeichen."
            )

        def _rename() -> None:
            coordinator.fritz_hosts.fc.call_action(
                "Hosts1",
                "X_AVM-DE_SetFriendlyNameByMAC",
                arguments={
                    "NewMACAddress": mac,
                    "NewX_AVM-DE_FriendlyName": name,
                },
            )

        try:
            await hass.async_add_executor_job(_rename)
        except FritzAuthorizationError as err:
            raise HomeAssistantError(
                "Umbenennen abgelehnt (fehlende Rechte). Das FRITZ!Box-Benutzerkonto "
                "der Integration braucht dafuer das Zugriffsrecht 'App' - unter "
                "FRITZ!Box-Oberflaeche > System > FRITZ!Box-Benutzer pruefen."
            ) from err
        except FritzConnectionException as err:
            raise HomeAssistantError(
                f"Umbenennen von {mac} fehlgeschlagen: {err}"
            ) from err
        await coordinator.async_request_refresh()

    async def _handle_wake_on_lan(call: ServiceCall) -> None:
        coordinator = _resolve_coordinator(call.data)
        mac = normalize_mac(call.data[ATTR_MAC])

        def _wake() -> None:
            coordinator.fritz_hosts.fc.call_action(
                "Hosts1", "X_AVM-DE_WakeOnLANByMACAddress", NewMACAddress=mac
            )

        try:
            await hass.async_add_executor_job(_wake)
        except FritzConnectionException as err:
            raise HomeAssistantError(
                f"Aufwecken von {mac} fehlgeschlagen: {err}"
            ) from err

    async def _handle_set_internet_access(call: ServiceCall) -> None:
        """Sperrt oder erlaubt den Internetzugang eines Geraets (optional mit Frist)."""
        await _resolve_coordinator(call.data).async_set_internet_access(
            call.data[ATTR_MAC],
            bool(call.data[ATTR_BLOCKED_PARAM]),
            call.data.get(ATTR_MINUTES),
        )

    async def _handle_set_mac_filter(call: ServiceCall) -> None:
        """Schaltet den WLAN-MAC-Filter dauerhaft an oder aus."""
        await _resolve_coordinator(call.data).async_set_mac_filter(call.data[ATTR_ENABLED])

    async def _handle_start_pairing(call: ServiceCall) -> None:
        """Schaltet den MAC-Filter fuer einige Minuten aus (Pairing)."""
        await _resolve_coordinator(call.data).async_start_pairing(call.data.get(ATTR_MINUTES))

    async def _handle_reboot_mesh(call: ServiceCall) -> None:
        """Startet Repeater und FRITZ!Box neu (Repeater zuerst)."""
        await _resolve_coordinator(call.data).async_reboot_mesh()

    async def _handle_gast_wlan_info(call: ServiceCall) -> dict[str, Any]:
        """Liefert SSID, Status und einen QR-Code fuers Gast-WLAN (Idee 11).

        Gibt die Zugangsdaten AUSSCHLIESSLICH als Dienst-Rueckgabe zurueck
        (``SupportsResponse.ONLY``) - sie landen damit nie in einem
        Sensor-Attribut oder im Verlauf. Das ist eine ausdrueckliche Vorgabe
        aus feature-ideen.md zu dieser Idee: "Der Schluessel darf nur in der
        Karte erscheinen, nicht in Sensor-Attributen/Verlauf." Dienst-
        Rueckgaben durchlaufen den Recorder nicht, im Unterschied zu
        Entitaets-Zustaenden/-Attributen.

        Der QR-Code wird mit der bereits in ``fritzconnection`` (Version
        1.15.1, ``lib.fritzwlan.FritzWLAN.get_wifi_qr_code``) eingebauten
        Funktion erzeugt, die intern ``segno`` nutzt - belegt per Quelltext
        und an echten Beispielen (verschiedene SSIDs/Passwoerter, auch mit
        Sonderzeichen wie ``;``/``\\``/``:`` sowie ein offenes Netz ohne
        Passwort) mit ``zbarimg`` erfolgreich rueckdekodiert. Dieser Dienst
        schreibt also KEINEN eigenen QR-Code-Generator, sondern verlaesst
        sich auf die bereits getestete, gepinnte Bibliothek.
        """
        coordinator = _resolve_coordinator(call.data)
        wlan = (coordinator.data or {}).get("wlan") or {}
        if f"wlan{GAST_WLAN_SERVICE_INDEX}" not in wlan:
            raise HomeAssistantError(
                "Diese FRITZ!Box bietet kein separates Gast-WLAN (Dienst "
                f"WLANConfiguration{GAST_WLAN_SERVICE_INDEX} wurde nicht "
                "gefunden)."
            )

        def _fetch() -> dict[str, Any]:
            guest = FritzWLAN(
                fc=coordinator.fritz_hosts.fc, service=GAST_WLAN_SERVICE_INDEX
            )
            info = guest.get_info()
            enabled = bool(info.get("NewEnable"))
            ssid = str(info.get("NewSSID") or "")
            offen = str(info.get("NewBeaconType") or "") in _OPEN_BEACON_TYPES
            password = None if offen else guest.get_password()

            qr_code_svg_base64 = None
            try:
                stream = guest.get_wifi_qr_code(kind="svg", scale=6, border=1)
            except AttributeError as err:
                # Laut fritzconnection-Quelltext der erwartete Fehler, wenn
                # segno (siehe manifest.json) ausnahmsweise doch fehlt.
                raise HomeAssistantError(
                    "Das Python-Paket 'segno' fehlt - es wird fuer den "
                    "QR-Code benoetigt und sollte mit der Integration "
                    "automatisch installiert worden sein. Bitte Home "
                    "Assistant neu starten; hilft das nicht, die "
                    "Integration einmal entfernen und neu einrichten."
                ) from err
            else:
                qr_code_svg_base64 = base64.b64encode(stream.read()).decode("ascii")

            return {
                "ssid": ssid,
                "eingeschaltet": enabled,
                "offen": offen,
                "passwort": password,
                "qr_code_svg_base64": qr_code_svg_base64,
            }

        try:
            return await hass.async_add_executor_job(_fetch)
        except FritzServiceError as err:
            raise HomeAssistantError(
                "Diese FRITZ!Box stellt die Gast-WLAN-Zugangsdaten ueber "
                f"TR-064 nicht wie erwartet bereit: {err}"
            ) from err
        except FritzConnectionException as err:
            raise HomeAssistantError(
                f"Gast-WLAN-Zugangsdaten konnten nicht gelesen werden: {err}"
            ) from err

    async def _handle_set_device_note(call: ServiceCall) -> None:
        """Setzt Etikett, Notiz und "reserviert"-Markierung eines Geraets (Idee 3).

        Nur in Home Assistant gespeichert - die FRITZ!Box wird nicht
        angesprochen. Nicht uebergebene Felder bleiben unveraendert; ein
        leerer Text loescht das jeweilige Feld.
        """
        coordinator = _resolve_coordinator(call.data)
        await coordinator.async_set_note(
            call.data[ATTR_MAC],
            label=call.data.get(ATTR_LABEL),
            note=call.data.get(ATTR_NOTE),
            reserved=call.data.get(ATTR_RESERVED),
        )

    async def _handle_update_oui(call: ServiceCall) -> dict[str, Any]:
        """Aktualisiert die Herstellerliste aus den IEEE-Registern (Idee 4b)."""
        counts = await _resolve_coordinator(call.data).async_update_oui()
        return {"eintraege": counts, "gesamt": sum(counts.values())}

    async def _handle_list_profiles(call: ServiceCall) -> dict[str, Any]:
        """Listet die Zugangsprofile der Kindersicherung (experimentell)."""
        profiles = await _resolve_coordinator(call.data).async_list_access_profiles()
        return {"profile": profiles}

    async def _handle_get_profile(call: ServiceCall) -> dict[str, Any]:
        """Liefert das aktuelle Zugangsprofil eines Geraets (experimentell)."""
        return await _resolve_coordinator(call.data).async_get_access_profile(call.data[ATTR_MAC])

    async def _handle_set_profile(call: ServiceCall) -> dict[str, Any]:
        """Weist einem Geraet ein Zugangsprofil zu, optional mit Frist (experimentell)."""
        return await _resolve_coordinator(call.data).async_set_access_profile(
            call.data[ATTR_MAC], call.data[ATTR_PROFILE], call.data.get(ATTR_MINUTES)
        )

    async def _handle_install_blueprints(call: ServiceCall) -> dict[str, Any]:
        """Kopiert die mitgelieferten Blueprints in das Konfigurationsverzeichnis."""
        return await _resolve_coordinator(call.data).async_install_blueprints(
            bool(call.data.get(ATTR_OVERWRITE, False))
        )

    for name, handler, schema, response in (
        (SERVICE_INSTALL_BLUEPRINTS, _handle_install_blueprints, INSTALL_BLUEPRINTS_SCHEMA, SupportsResponse.OPTIONAL),
        (SERVICE_LIST_ACCESS_PROFILES, _handle_list_profiles, LIST_PROFILES_SCHEMA, SupportsResponse.ONLY),
        (SERVICE_GET_ACCESS_PROFILE, _handle_get_profile, GET_PROFILE_SCHEMA, SupportsResponse.ONLY),
        (SERVICE_SET_ACCESS_PROFILE, _handle_set_profile, SET_PROFILE_SCHEMA, SupportsResponse.OPTIONAL),
    ):
        if not hass.services.has_service(DOMAIN, name):
            hass.services.async_register(
                DOMAIN, name, handler, schema=schema, supports_response=response
            )

    if not hass.services.has_service(DOMAIN, SERVICE_SET_DEVICE_NAME):
        hass.services.async_register(
            DOMAIN, SERVICE_SET_DEVICE_NAME, _handle_set_device_name, schema=MAC_SCHEMA
        )
    if not hass.services.has_service(DOMAIN, SERVICE_WAKE_ON_LAN):
        hass.services.async_register(
            DOMAIN, SERVICE_WAKE_ON_LAN, _handle_wake_on_lan, schema=MAC_SCHEMA
        )
    if not hass.services.has_service(DOMAIN, SERVICE_SET_INTERNET_ACCESS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_INTERNET_ACCESS,
            _handle_set_internet_access,
            schema=INTERNET_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_SET_MAC_FILTER):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_MAC_FILTER,
            _handle_set_mac_filter,
            schema=MAC_FILTER_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_START_PAIRING):
        hass.services.async_register(
            DOMAIN,
            SERVICE_START_PAIRING,
            _handle_start_pairing,
            schema=PAIRING_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_REBOOT_MESH):
        hass.services.async_register(
            DOMAIN, SERVICE_REBOOT_MESH, _handle_reboot_mesh, schema=REBOOT_MESH_SCHEMA
        )
    if not hass.services.has_service(DOMAIN, SERVICE_GAST_WLAN_INFO):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GAST_WLAN_INFO,
            _handle_gast_wlan_info,
            schema=GAST_WLAN_INFO_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_SET_DEVICE_NOTE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_DEVICE_NOTE,
            _handle_set_device_note,
            schema=DEVICE_NOTE_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_UPDATE_OUI):
        hass.services.async_register(
            DOMAIN,
            SERVICE_UPDATE_OUI,
            _handle_update_oui,
            schema=UPDATE_OUI_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )
