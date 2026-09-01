"""Die Integration fritzbox_netzwerk."""

from __future__ import annotations

import logging
import os

import voluptuous as vol
from fritzconnection import FritzConnection
from fritzconnection.core.exceptions import (
    FritzAuthorizationError,
    FritzConnectionException,
    FritzSecurityError,
    FritzServiceError,
)
from fritzconnection.lib.fritzhosts import FritzHosts
from requests.exceptions import ConnectionError as RequestsConnectionError

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_BLOCKED_PARAM,
    ATTR_MAC,
    ATTR_NAME,
    CARD_FILENAME,
    CARD_URL,
    CONF_USE_TLS,
    DEFAULT_USE_TLS,
    DOMAIN,
    PLATFORMS,
    SERVICE_SET_DEVICE_NAME,
    SERVICE_SET_INTERNET_ACCESS,
    SERVICE_WAKE_ON_LAN,
    URL_BASE,
    VERSION,
)
from .coordinator import FritzboxNetzwerkCoordinator
from .hosts import mac_key, normalize_mac

_LOGGER = logging.getLogger(__name__)

type FritzboxNetzwerkConfigEntry = ConfigEntry[FritzboxNetzwerkCoordinator]

MAC_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MAC): cv.string,
        vol.Optional(ATTR_NAME): cv.string,
    }
)

INTERNET_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MAC): cv.string,
        vol.Required(ATTR_BLOCKED_PARAM): cv.boolean,
    }
)


async def async_setup_entry(
    hass: HomeAssistant, entry: FritzboxNetzwerkConfigEntry
) -> bool:
    """Richtet einen Konfigurationseintrag ein."""

    def _connect() -> FritzHosts:
        connection = FritzConnection(
            address=entry.data[CONF_HOST],
            user=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            use_tls=entry.data.get(CONF_USE_TLS, DEFAULT_USE_TLS),
        )
        return FritzHosts(fc=connection)

    try:
        fritz_hosts = await hass.async_add_executor_job(_connect)
    except (FritzSecurityError, FritzAuthorizationError) as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except (FritzConnectionException, RequestsConnectionError) as err:
        raise ConfigEntryNotReady(
            f"FRITZ!Box unter {entry.data[CONF_HOST]} nicht erreichbar: {err}"
        ) from err

    coordinator = FritzboxNetzwerkCoordinator(hass, entry, fritz_hosts)
    await coordinator.async_load_last_seen()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await _async_register_card(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_register_services(hass)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: FritzboxNetzwerkConfigEntry
) -> bool:
    """Entlaedt einen Konfigurationseintrag."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded and not hass.config_entries.async_loaded_entries(DOMAIN):
        for service in (
            SERVICE_SET_DEVICE_NAME,
            SERVICE_WAKE_ON_LAN,
            SERVICE_SET_INTERNET_ACCESS,
        ):
            hass.services.async_remove(DOMAIN, service)
    return unloaded


async def _async_update_listener(
    hass: HomeAssistant, entry: FritzboxNetzwerkConfigEntry
) -> None:
    """Laedt den Eintrag nach Aenderung der Optionen neu."""
    await hass.config_entries.async_reload(entry.entry_id)


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

    def _first_coordinator() -> FritzboxNetzwerkCoordinator:
        entries = hass.config_entries.async_loaded_entries(DOMAIN)
        if not entries:
            raise HomeAssistantError("Keine eingerichtete FRITZ!Box gefunden")
        return entries[0].runtime_data

    async def _handle_set_device_name(call: ServiceCall) -> None:
        coordinator = _first_coordinator()
        mac = normalize_mac(call.data[ATTR_MAC])
        name = call.data.get(ATTR_NAME, "")
        if not name:
            raise HomeAssistantError("Es wurde kein neuer Name uebergeben")
        try:
            await hass.async_add_executor_job(
                coordinator.fritz_hosts.set_host_name, mac, name
            )
        except FritzConnectionException as err:
            raise HomeAssistantError(
                f"Umbenennen von {mac} fehlgeschlagen: {err}"
            ) from err
        await coordinator.async_request_refresh()

    async def _handle_wake_on_lan(call: ServiceCall) -> None:
        coordinator = _first_coordinator()
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
        """Sperrt oder erlaubt den Internetzugang eines Geraets.

        Die FRITZ!Box-Aktion arbeitet mit der IPv4-Adresse. Diese kann sich
        per DHCP aendern, deshalb wird der stabilere MAC-Schluessel
        uebergeben und hier aus der aktuellen Hostliste aufgeloest.
        """
        coordinator = _first_coordinator()
        mac = normalize_mac(call.data[ATTR_MAC])
        blocked = bool(call.data[ATTR_BLOCKED_PARAM])
        key = mac_key(mac)

        ip = ""
        for host in (coordinator.data or {}).get("hosts", []):
            if mac_key(host.get("mac")) == key:
                ip = str(host.get("ip") or "")
                break
        if not ip:
            raise HomeAssistantError(
                f"Zu {mac} ist derzeit keine IP-Adresse bekannt - ist das Geraet "
                "der FRITZ!Box bekannt und hat es eine IPv4-Adresse?"
            )

        def _set() -> None:
            coordinator.fritz_hosts.fc.call_action(
                "X_AVM-DE_HostFilter1",
                "DisallowWANAccessByIP",
                NewIPv4Address=ip,
                NewDisallow=blocked,
            )

        try:
            await hass.async_add_executor_job(_set)
        except FritzServiceError as err:
            raise HomeAssistantError(
                "Diese FRITZ!Box stellt das Sperren des Internetzugangs ueber "
                "TR-064 nicht bereit (Dienst X_AVM-DE_HostFilter fehlt)."
            ) from err
        except FritzConnectionException as err:
            raise HomeAssistantError(
                f"Internetzugang fuer {mac} ({ip}) konnte nicht geaendert werden: {err}"
            ) from err
        await coordinator.async_request_refresh()

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
