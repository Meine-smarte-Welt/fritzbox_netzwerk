"""Datenabruf fuer fritzbox_netzwerk."""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import threading
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, Final
from xml.etree.ElementTree import ParseError

from fritzconnection import FritzConnection
from fritzconnection.core.exceptions import (
    FritzAuthorizationError,
    FritzConnectionException,
    FritzSecurityError,
    FritzServiceError,
)
from fritzconnection.lib.fritzhosts import FritzHosts
from fritzconnection.lib.fritzstatus import FritzStatus
import requests
from requests.exceptions import RequestException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later, async_track_point_in_utc_time
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .auth_guard import AUTH_FAILURE_LIMIT, AuthFailureGuard
from .const import (
    CONF_ADDRESS_SOURCE_INTERVAL,
    BLUEPRINTS_DIRNAME,
    CONF_CHECK_UPDATES,
    CONF_ENABLE_PARENTAL,
    DEFAULT_CHECK_UPDATES,
    GITHUB_LATEST_RELEASE_URL,
    UPDATE_CHECK_HOURS,
    VERSION,
    CONF_ENABLE_SYSTEM_STATS,
    DEFAULT_ENABLE_PARENTAL,
    PROFILE_REVERT_STORAGE_VERSION,
    CONF_REMOTE_ACCESS,
    DEFAULT_ENABLE_SYSTEM_STATS,
    INTERNET_BLOCK_STORAGE_VERSION,
    SYSTEM_STATS_INTERVAL_MINUTES,
    CONF_SCAN_INTERVAL,
    CONF_TRACK_ADDRESS_SOURCE,
    CONF_TRACK_WLAN_BAND,
    CONF_USE_TLS,
    DEFAULT_ADDRESS_SOURCE_INTERVAL,
    DEFAULT_PAIRING_MINUTES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TRACK_ADDRESS_SOURCE,
    DEFAULT_TRACK_WLAN_BAND,
    DEFAULT_USE_TLS,
    DHCP_POOL_INTERVAL_MINUTES,
    DOMAIN,
    CONF_PAIRING_MINUTES,
    FIRST_SEEN_STORAGE_VERSION,
    LAST_SEEN_STORAGE_VERSION,
    NOTES_STORAGE_VERSION,
    OUI_CUSTOM_FILENAME,
    OUI_UPDATE_FILENAME,
    PAIRING_STORAGE_VERSION,
    USER_DATA_DIRNAME,
)
from .hosts import (
    IEEE_REGISTER_URLS,
    MAC_FILTER_INFO_KEY,
    MIN_MA_L_ENTRIES,
    UPNP_ALREADY_TERMINATED,
    UPNP_DISCONNECT_IN_PROGRESS,
    as_bool,
    build_hosts,
    classify_ip_with_reserved,
    dhcp_pool,
    frequency_band,
    is_mac_filter_band,
    is_repeater,
    list_path,
    load_notes,
    load_oui,
    mac_key,
    make_note_entry,
    merge_oui,
    mesh_members,
    mesh_reboot_plan,
    parse_ieee_csv,
    parse_oui,
    parse_wlan_device_list,
    reconnect_plan,
    set_config_arguments,
    summarize,
    serialize_oui,
    to_kbytes_per_s,
    to_mbit_per_s,
    upnp_error_code,
    validate_custom_oui_lines,
    wan_kind,
    wlan_bands,
)
from .blueprints_install import install_blueprints
from .mesh_topology import fetch_mesh_links
from .updates import build_version_info, parse_release
from .webui import (
    assign_profile,
    base_url,
    fetch_system_stats,
    get_device_profile,
    list_profiles,
)

_LOGGER = logging.getLogger(__name__)

# Nach einer ausgeloesten Neuverbindung wird ein weiterer Druck auf den
# Button so lange ignoriert (Sekunden). Die Box braucht die Zeit fuer die
# neue Einwahl; ein zweites ForceTermination wuerde sie nur mit Fehler 707
# (DisconnectInProgress) oder 711 (ConnectionAlreadyTerminated) ablehnen.
RECONNECT_COOLDOWN: Final = 30

# Zeitlimit fuer die Verbindung zu einem Repeater (Sekunden).
REPEATER_TIMEOUT: Final = 15

# Pause zwischen dem Neustart der Repeater und dem der FRITZ!Box (Sekunden):
# Die Repeater sollen den Befehl sicher bekommen, bevor das Netz wegbricht.
MESH_REBOOT_DELAY: Final = 3

# Bis zum naechsten Versuch, den MAC-Filter nach dem Pairing wieder
# einzuschalten, falls die FRITZ!Box gerade nicht antwortet (Sekunden).
PAIRING_RETRY_SECONDS: Final = 60

# Dienste, die den MAC-Filter tragen: Hauptband(er), nicht das Gast-WLAN.
MAC_FILTER_SERVICES: Final = (1, 2)

# WLAN-Band je Geraet: hoechster abgefragter WLANConfiguration-Dienst (AVM
# beschreibt bis zu vier: drei Funkmodule plus Gast) und Zeitlimit fuer den
# Abruf der Geraeteliste (Sekunden).
WLAN_BAND_MAX_SERVICE: Final = 4
WLAN_LIST_TIMEOUT: Final = 10

# Herstellertabelle (OUI), die mit der Integration ausgeliefert wird.
OUI_FILE: Final = os.path.join(os.path.dirname(__file__), "data", "oui.txt")


class MacFilterUnsupported(FritzConnectionException):
    """Die FRITZ!Box bietet den MAC-Filter ueber TR-064 nicht an."""


class MacFilterNotApplied(FritzConnectionException):
    """Die FRITZ!Box hat die Aenderung angenommen, aber nicht uebernommen."""


class FritzboxNetzwerkCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Haelt die Geraeteliste der FRITZ!Box aktuell.

    Die eigentliche Hostliste kommt mit EINEM SOAP-Aufruf
    (``X_AVM-DE_GetHostListPath``). Die Angabe DHCP/statisch steht dort
    nicht drin - sie ist nur ueber ``GetSpecificHostEntry`` je Geraet zu
    bekommen. Diese teure Abfrage laeuft deshalb in einem eigenen,
    deutlich langsameren Takt und ihr Ergebnis wird zwischengespeichert.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        fritz_hosts: FritzHosts,
        auth_guard: AuthFailureGuard | None = None,
    ) -> None:
        """Initialisiert den Coordinator."""
        self.entry = entry
        self.fritz_hosts = fritz_hosts
        # Zaehlt aufeinanderfolgende abgelehnte Anmeldungen (siehe auth_guard.py):
        # eine einzelne kurzzeitige Ablehnung durch die Box verlangt noch keine
        # erneute Anmeldung.
        self._auth_guard = auth_guard or AuthFailureGuard()
        self._address_sources: dict[str, dict[str, Any]] = {}
        self._address_source_scan: datetime | None = None
        self._address_source_failed = False
        # DHCP-Bereich der Box (erste, letzte Adresse als Zahl): dient der
        # Einordnung fest/dynamisch (siehe hosts.classify_ip) und - seit 1.6.3 -
        # dem Sensor "Belegte Adressen im Pool" (Idee 8 aus feature-ideen.md).
        # Laeuft in einem eigenen, sehr langsamen Takt (siehe
        # ``_dhcp_pool_due``), unabhaengig von der IP-Typ-Erfassung, damit der
        # Sensor auch ohne diese Option entsteht.
        self._dhcp_pool: tuple[int, int] | None = None
        self._dhcp_pool_scan: datetime | None = None

        # WLAN-Band je Geraet: Frequenzband je WLANConfiguration-Dienst (wird
        # einmal gelesen) und Dienste, die die Box nicht hat.
        self._wlan_service_band: dict[int, str] = {}
        self._wlan_service_absent: set[int] = set()

        # Mesh-Topologie (Idee 5 aus feature-ideen.md): wird nur abgefragt,
        # wenn im VORIGEN Zyklus ein Repeater in der Hostliste stand - ein
        # zusaetzlicher HTTP-Abruf pro Aktualisierung lohnt sich nicht fuer
        # die meisten Installationen (eine einzelne FRITZ!Box ohne Mesh).
        self._repeater_seen = False
        self._mesh_topology_supported = True

        # Herstellertabelle (MAC-Praefix -> Name); wird einmal beim Start
        # geladen, siehe ``async_load_oui``. Bleibt sie leer, fehlt nur die
        # Herstellerangabe.
        self._oui: dict[str, str] = {}
        # Herkunft der Tabelle fuer Diagnose/Antworten: Eintraege je Schicht.
        self.oui_stats: dict[str, int] = {}
        self._oui_update_lock = asyncio.Lock()

        # Idee 21 (experimentell): CPU/RAM aus der Weboberflaeche, eigener
        # langsamer Takt, Fehler fuehren nur zu fehlenden Werten.
        self._system_stats: dict[str, float | None] | None = None
        self._system_stats_scan: datetime | None = None
        self._system_stats_error: str | None = None

        # Internetsperre mit Frist (Idee 22): MAC-Schluessel -> Ende (ISO-UTC),
        # dauerhaft gespeichert, damit ein Neustart die Sperre nicht "vergisst".
        self._block_until: dict[str, str] = {}
        self._block_store: Store[dict[str, str]] = Store(
            hass, INTERNET_BLOCK_STORAGE_VERSION, f"{DOMAIN}.internet_block.{entry.entry_id}"
        )

        # Versionspruefung gegen GitHub (taeglich, abschaltbar).
        self._latest_release: dict[str, str] | None = None
        self._version_checked: datetime | None = None

        # Kindersicherung (Idee 22, experimentell): zeitlich begrenzter
        # Profilwechsel - MAC-Schluessel -> {profile: urspruengliches Profil,
        # until: Ende}. Dauerhaft gespeichert (ueberlebt einen Neustart).
        self._profile_revert: dict[str, dict[str, str]] = {}
        self._profile_store: Store[dict[str, dict[str, str]]] = Store(
            hass, PROFILE_REVERT_STORAGE_VERSION, f"{DOMAIN}.profile_revert.{entry.entry_id}"
        )

        # Eigene Notizen/Etiketten/"reserviert"-Markierungen je Geraet
        # (Idee 3): nur hier in Home Assistant gespeichert, die FRITZ!Box wird
        # nicht veraendert. Schluessel ist der MAC-Schluessel.
        self._notes: dict[str, dict[str, Any]] = {}
        self._notes_store: Store[dict[str, Any]] = Store(
            hass, NOTES_STORAGE_VERSION, f"{DOMAIN}.notes.{entry.entry_id}"
        )

        # Verbindungsdaten (Down/Up). FritzStatus teilt sich die Verbindung
        # mit FritzHosts. Fehlt der WAN-Dienst (z. B. FRITZ!Box im reinen
        # Access-Point-Betrieb), wird nach dem ersten Fehlschlag nicht mehr
        # abgefragt, um das Protokoll nicht vollzuschreiben.
        self._fritz_status: FritzStatus | None = None
        self._connection_supported = True

        # Externe IP: nur der zuletzt gesehene Wert (nicht gespeichert - nach
        # einem Neustart von Home Assistant ist ein "Aenderung erkannt" ins
        # Leere ohnehin falsch, deshalb wird beim ersten Abruf nie ausgeloest).
        self._last_external_ip: str | None = None
        self._external_ip_listeners: list[Callable[[str, str], None]] = []

        # "Neues Geraet"-Ereignis: beim allerersten Abruf nach einer frischen
        # Einrichtung (noch kein gespeichertes "zuletzt gesehen") wuerde sonst
        # das gesamte vorhandene Heimnetz als "neu" gemeldet. Gesetzt in
        # ``async_load_last_seen()``.
        self._new_device_baseline_pending = True
        self._new_device_listeners: list[Callable[[dict[str, Any]], None]] = []

        # Neuverbindung: nie zwei gleichzeitig, und kurz nach einer
        # erfolgreichen keine weitere (siehe ``RECONNECT_COOLDOWN``).
        self._reconnect_lock = threading.Lock()
        self._last_reconnect: float | None = None

        # WLAN-Baender fuer die Steuerung: gemerkt wird, welche Dienste die
        # Box bereitstellt (1=2,4 GHz, 2=5 GHz, 3=Gast bei Dualband).
        self._wlan_supported: dict[int, bool] = {1: True, 2: True, 3: True}

        # "Zuletzt gesehen" pflegt die Integration selbst (die FRITZ!Box
        # liefert es nicht) und speichert es dauerhaft, damit die Angabe
        # einen Neustart uebersteht.
        self._last_seen: dict[str, str] = {}
        self._last_seen_store: Store[dict[str, str]] = Store(
            hass, LAST_SEEN_STORAGE_VERSION, f"{DOMAIN}.last_seen.{entry.entry_id}"
        )

        # "Zum ersten Mal gesehen" (seit 1.6.3, fuer den Karten-Filter
        # "Neu (letzte 7 Tage)"): wird NUR geschrieben, wenn ein Geraet
        # ueber ``_process_new_devices`` als neu erkannt wird - siehe dort
        # und ``hosts.apply_first_seen`` fuer die Begruendung, warum bereits
        # laenger bekannte Geraete hier bewusst keinen Wert bekommen.
        self._first_seen: dict[str, str] = {}
        self._first_seen_store: Store[dict[str, str]] = Store(
            hass, FIRST_SEEN_STORAGE_VERSION, f"{DOMAIN}.first_seen.{entry.entry_id}"
        )

        # Pairing (MAC-Filter zeitweise aus): Der Zeitpunkt, zu dem der Filter
        # wieder eingeschaltet wird, wird dauerhaft gespeichert. Startet Home
        # Assistant waehrenddessen neu, holt ``async_restore_pairing`` das nach -
        # der Filter bleibt so nicht versehentlich dauerhaft offen.
        self._pairing_until: datetime | None = None
        self._pairing_cancel: CALLBACK_TYPE | None = None
        self._pairing_store: Store[dict[str, str]] = Store(
            hass, PAIRING_STORAGE_VERSION, f"{DOMAIN}.pairing.{entry.entry_id}"
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )

    # -- Optionen ---------------------------------------------------------

    @property
    def track_address_source(self) -> bool:
        """Ob DHCP/statisch mit erfasst werden soll."""
        return self.entry.options.get(
            CONF_TRACK_ADDRESS_SOURCE, DEFAULT_TRACK_ADDRESS_SOURCE
        )

    @property
    def track_wlan_band(self) -> bool:
        """Ob das WLAN-Band je Geraet erfasst werden soll."""
        return self.entry.options.get(CONF_TRACK_WLAN_BAND, DEFAULT_TRACK_WLAN_BAND)

    @property
    def dhcp_pool(self) -> tuple[int, int] | None:
        """DHCP-Bereich der Box (erste, letzte Adresse als Zahl), siehe hosts.dhcp_pool.

        ``None``, wenn der DHCP-Server aus ist oder der Bereich (noch) nicht
        ermittelbar war - der Sensor "Belegte Adressen im Pool" (Idee 8)
        entsteht dann (noch) nicht.
        """
        return self._dhcp_pool

    @property
    def address_source_interval(self) -> timedelta:
        """Abstand zwischen zwei IP-Typ-Abfragen."""
        return timedelta(
            minutes=self.entry.options.get(
                CONF_ADDRESS_SOURCE_INTERVAL, DEFAULT_ADDRESS_SOURCE_INTERVAL
            )
        )

    # -- Abruf ------------------------------------------------------------

    def _address_sources_due(self) -> bool:
        """Prueft, ob die langsame IP-Typ-Abfrage jetzt faellig ist."""
        if not self.track_address_source:
            return False
        if self._address_source_scan is None:
            return True
        return dt_util.utcnow() - self._address_source_scan >= self.address_source_interval

    def _fetch_address_sources(self, macs: list[str]) -> None:
        """Holt DHCP/statisch je Geraet (ein SOAP-Aufruf pro MAC-Adresse)."""
        sources: dict[str, dict[str, Any]] = {}
        for mac in macs:
            if not mac:
                continue
            try:
                entry = self.fritz_hosts.get_specific_host_entry(mac)
            except FritzConnectionException as err:
                # Einzelne Geraete koennen der FRITZ!Box unbekannt sein
                # (z. B. Mesh-Clients hinter einem Repeater). Das ist kein
                # Grund, die gesamte Aktualisierung scheitern zu lassen.
                _LOGGER.debug("IP-Typ fuer %s nicht abrufbar: %s", mac, err)
                continue
            _LOGGER.debug(
                "IP-Typ %s: AddressSource=%s, LeaseTimeRemaining=%s",
                mac,
                entry.get("NewAddressSource"),
                entry.get("NewLeaseTimeRemaining"),
            )
            sources[mac_key(mac)] = {
                "address_source": entry.get("NewAddressSource"),
                "lease_time_remaining": entry.get("NewLeaseTimeRemaining"),
            }
        self._address_sources = sources

    def _dhcp_pool_due(self) -> bool:
        """Ob der DHCP-Bereich neu abgefragt werden soll.

        Eigener, fester Takt (``DHCP_POOL_INTERVAL_MINUTES``) statt eines
        Mitlaufens mit ``_address_sources_due()``: der Bereich wird auch
        gebraucht, wenn die IP-Typ-Erfassung ausgeschaltet ist (Sensor
        "Belegte Adressen im Pool", Idee 8 aus feature-ideen.md).
        """
        if self._dhcp_pool_scan is None:
            return True
        return dt_util.utcnow() - self._dhcp_pool_scan >= timedelta(
            minutes=DHCP_POOL_INTERVAL_MINUTES
        )

    def _fetch_dhcp_pool(self) -> tuple[int, int] | None:
        """DHCP-Bereich der FRITZ!Box (None, wenn nicht ermittelbar)."""
        try:
            info = self.call_action("LANHostConfigManagement1", "GetInfo")
        except (FritzConnectionException, RequestException) as err:
            _LOGGER.debug("DHCP-Bereich nicht abrufbar: %s", err)
            return None
        pool = dhcp_pool(info)
        _LOGGER.debug(
            "DHCP-Bereich: %s - %s",
            info.get("NewMinAddress"),
            info.get("NewMaxAddress"),
        )
        return pool

    def _fetch(
        self,
    ) -> tuple[
        list[dict[str, Any]],
        bool,
        dict[str, Any] | None,
        dict[str, bool],
        dict[str, str],
        dict[str, dict[str, Any]],
    ]:
        """Blockierender Teil des Abrufs, laeuft im Executor."""
        raw_hosts = self.fritz_hosts.get_hosts_attributes()
        refreshed = False
        if self._address_sources_due():
            macs = [str(host.get("MACAddress") or "") for host in raw_hosts]
            self._fetch_address_sources(macs)
            refreshed = True
        if self._dhcp_pool_due():
            self._dhcp_pool = self._fetch_dhcp_pool()
            self._dhcp_pool_scan = dt_util.utcnow()
        connection = self._fetch_connection()
        wlan = self._fetch_wlan() if self._controls_enabled else {}
        bands = self._fetch_wlan_bands() if self.track_wlan_band else {}
        mesh_links = self._fetch_mesh_topology() if self._repeater_seen else {}
        if self.system_stats_enabled and self._system_stats_due():
            self._system_stats = self._fetch_system_stats()
            self._system_stats_scan = dt_util.utcnow()
        return raw_hosts, refreshed, connection, wlan, bands, mesh_links

    @property
    def system_stats_enabled(self) -> bool:
        """Ob CPU/RAM aus der Weboberflaeche gelesen werden sollen (experimentell)."""
        return bool(
            self.entry.options.get(CONF_ENABLE_SYSTEM_STATS, DEFAULT_ENABLE_SYSTEM_STATS)
        )

    @property
    def system_stats(self) -> dict[str, float | None] | None:
        """Letzte gelesene Werte (``cpu``, ``ram``, ``temperature``) oder ``None``."""
        return self._system_stats

    @property
    def system_stats_error(self) -> str | None:
        """Grund des letzten Fehlschlags (fuer Diagnose), sonst ``None``."""
        return self._system_stats_error

    def _run_web(self, func: Callable[..., Any], *args: Any) -> Any:
        """Fuehrt eine Weboberflaechen-Funktion aus ``webui`` aus (blockierend).

        Gleiche Zugangsdaten wie TR-064. Lokal ist die Oberflaeche unter dem
        Standardport erreichbar, bei Fernzugriff per HTTPS auf dem
        konfigurierten Port.
        """
        fc = self.fritz_hosts.fc
        remote = bool(self.entry.data.get(CONF_REMOTE_ACCESS, False))
        base = base_url(str(fc.address), getattr(fc, "port", None), remote)
        with requests.Session() as session:
            # Wie fritzconnection: Boxen nutzen meist ein selbstsigniertes Zertifikat.
            session.verify = False
            return func(
                session,
                base,
                str(self.entry.data.get(CONF_USERNAME) or ""),
                str(self.entry.data.get(CONF_PASSWORD) or ""),
                *args,
            )

    def _system_stats_due(self) -> bool:
        if self._system_stats_scan is None:
            return True
        return dt_util.utcnow() - self._system_stats_scan >= timedelta(
            minutes=SYSTEM_STATS_INTERVAL_MINUTES
        )

    def _fetch_system_stats(self) -> dict[str, float | None] | None:
        """Liest CPU/RAM ueber die Weboberflaeche (blockierend, im Executor).

        Jeder Fehler ist harmlos: die Werte fehlen dann (bzw. bleiben die
        letzten stehen), die Geraeteliste laeuft unberuehrt weiter.
        """
        try:
            stats = self._run_web(fetch_system_stats)
        except (ValueError, RequestException) as err:
            if self._system_stats_error != str(err):
                _LOGGER.warning("CPU/RAM der Box nicht lesbar (experimentell): %s", err)
            self._system_stats_error = str(err)
            return self._system_stats
        self._system_stats_error = None
        return stats

    def _fetch_wlan_bands(self) -> dict[str, str]:
        """Ordnet WLAN-Geraete ihrem Funkband zu (``mac_key`` -> "2.4"/"5"/"6").

        Je vorhandenem WLAN-Dienst ein SOAP-Aufruf (Pfad der Geraeteliste)
        plus ein Abruf der XML-Liste; das Frequenzband des Dienstes wird nur
        beim ersten Mal gelesen. Jeder Fehler ist hier harmlos: es fehlt dann
        nur die Bandangabe, die Aktualisierung der Geraeteliste laeuft weiter.
        """
        bands: dict[str, str] = {}
        fc = self.fritz_hosts.fc
        for index in range(1, WLAN_BAND_MAX_SERVICE + 1):
            if index in self._wlan_service_absent:
                continue
            service = f"WLANConfiguration{index}"
            try:
                if index not in self._wlan_service_band:
                    info = self.call_action(service, "GetInfo")
                    self._wlan_service_band[index] = frequency_band(
                        info.get("NewX_AVM-DE_FrequencyBand")
                    )
                path = list_path(
                    self.call_action(service, "X_AVM-DE_GetWLANDeviceListPath")
                )
                if not path:
                    continue
                with fc.session.get(
                    f"{fc.address}:{fc.port}{path}", timeout=WLAN_LIST_TIMEOUT
                ) as response:
                    if not response.ok:
                        _LOGGER.debug(
                            "WLAN-Geraeteliste %s: HTTP %s", index, response.status_code
                        )
                        continue
                    text = response.text
                bands.update(
                    wlan_bands(
                        parse_wlan_device_list(text), self._wlan_service_band[index]
                    )
                )
            except FritzServiceError:
                # Diesen WLAN-Dienst gibt es an der Box nicht.
                self._wlan_service_absent.add(index)
            except (
                FritzConnectionException,
                RequestException,
                ParseError,
                KeyError,
                ValueError,
            ) as err:
                _LOGGER.debug("WLAN-Band (%s) nicht ermittelbar: %s", service, err)
        return bands

    def _fetch_mesh_topology(self) -> dict[str, dict[str, Any]]:
        """"Verbunden ueber" und Verbindungsrate je Geraet (Idee 5 aus feature-ideen.md).

        Die eigentliche Auswertung steckt in ``mesh_topology.py`` (von Home
        Assistant unabhaengig, siehe dort und ``tests/test_mesh_topology.py``);
        hier nur die Fehlerbehandlung drumherum. Nutzt
        ``fritzconnection.lib.fritztopology`` (Teil der mit diesem Projekt
        ausgelieferten, gepinnten Bibliotheksversion 1.15.1) ueber
        ``X_AVM-DE_GetMeshListPath`` - belegtes AVM-Schema
        (https://avm.de/service/schnittstellen/, "Mesh-Topologie").

        ANNAHME: das genaue JSON-Format (z. B. ob jede FRITZ!OS-Version
        wirklich fuer jedes Geraet genau eine aktive Verbindung meldet) ist
        nur gegen den tatsaechlichen Bibliotheks-Quelltext und eine von Hand
        nachgebaute Beispiel-Topologie geprueft, NICHT an einer echten
        FRITZ!Box - siehe Hinweis in ``mesh_topology.links_from_topology``.

        Jeder Fehler (z. B. eine Box, die den Dienst ablehnt, oder eine
        unerwartete Antwort) ist hier harmlos: es fehlt dann nur "verbunden
        ueber"/die Verbindungsrate, die Aktualisierung der Geraeteliste
        laeuft weiter. Nach einem Verbindungsfehlschlag wird der Abruf nicht
        mehr wiederholt, um das Protokoll nicht mit wiederkehrenden Fehlern
        vollzuschreiben (wie beim WAN-Dienst, siehe ``_fetch_connection``).
        """
        if not self._mesh_topology_supported:
            return {}
        try:
            return fetch_mesh_links(self.fritz_hosts.fc)
        except (FritzConnectionException, RequestException) as err:
            _LOGGER.debug("Mesh-Topologie nicht abrufbar: %s", err)
            self._mesh_topology_supported = False
            return {}
        except (KeyError, ValueError, TypeError, AttributeError) as err:
            # Unerwartete/unvollstaendige Antwort (z. B. ein Schema-Unterschied
            # zwischen FRITZ!OS-Versionen) - siehe Annahme-Hinweis oben.
            _LOGGER.debug("Mesh-Topologie: unerwartetes Format: %s", err)
            return {}

    @property
    def _controls_enabled(self) -> bool:
        """Ob die FRITZ!Box-Steuerung (WLAN/Reconnect/Neustart) aktiv ist."""
        from .const import CONF_ENABLE_CONTROLS, DEFAULT_ENABLE_CONTROLS

        return self.entry.options.get(CONF_ENABLE_CONTROLS, DEFAULT_ENABLE_CONTROLS)

    @property
    def controls_enabled(self) -> bool:
        """Oeffentlicher Zugriff auf den Steuerungs-Status (fuer den Sensor)."""
        return self._controls_enabled

    def call_action(self, service: str, action: str, **kwargs: Any) -> dict[str, Any]:
        """Fuehrt einen TR-064-Aufruf aus (blockierend, im Executor nutzen)."""
        return self.fritz_hosts.fc.call_action(service, action, **kwargs)

    def reconnect_internet(self) -> None:
        """Baut die Internetverbindung neu auf (neue oeffentliche IP).

        Blockierend, im Executor nutzen. Laeuft bereits eine Neuverbindung
        (zweiter Druck, Automation parallel) oder liegt die letzte weniger als
        ``RECONNECT_COOLDOWN`` Sekunden zurueck, passiert nichts - die Box
        waehlt sich ohnehin gerade neu ein.
        """
        if not self._reconnect_lock.acquire(blocking=False):
            _LOGGER.info("Neuverbindung laeuft bereits - weiterer Aufruf ignoriert")
            return
        try:
            now = time.monotonic()
            if (
                self._last_reconnect is not None
                and now - self._last_reconnect < RECONNECT_COOLDOWN
            ):
                _LOGGER.info(
                    "Neuverbindung vor weniger als %s s ausgeloest - "
                    "weiterer Aufruf ignoriert",
                    RECONNECT_COOLDOWN,
                )
                return
            self._force_reconnect()
            self._last_reconnect = time.monotonic()
        finally:
            self._reconnect_lock.release()

    def _wan_kind(self) -> str | None:
        """Verbindungsart, die die Box gerade nutzt (IP oder PPP), sonst None."""
        try:
            result = self.call_action("Layer3Forwarding1", "GetDefaultConnectionService")
        except (FritzConnectionException, RequestException) as err:
            _LOGGER.debug("Verbindungsart nicht ermittelbar: %s", err)
            return None
        kind = wan_kind(result.get("NewDefaultConnectionService"))
        _LOGGER.debug("Aktive Verbindungsart: %s", kind or "unbekannt")
        return kind

    def _force_reconnect(self) -> None:
        """Loest die Neuverbindung aus (siehe ``hosts.reconnect_plan``).

        Zuerst wird ermittelt, ob die Box per IP oder per PPP (DSL/PPPoE)
        online ist; deren Dienste kommen zuerst dran. So landet der Befehl
        nicht auf einem ungenutzten Dienst.

        Antworten der Box:
        - Dienst fehlt -> naechster Dienst.
        - 707 DisconnectInProgress: Die Trennung laeuft schon - das Ziel ist
          erreicht. Vom aktiven Dienst: fertig. Von einem anderen: weiter
          probieren, am Ende aber als Erfolg werten.
        - 711 ConnectionAlreadyTerminated vom aktiven Dienst: Die Verbindung
          ist schon getrennt - dann wird sie mit ``RequestConnection`` neu
          aufgebaut.
        - sonstiger Fehler -> naechster Dienst. Geht nichts durch, wird der
          Fehler des ERSTEN echten Versuchs weitergereicht.
        """
        first_error: FritzConnectionException | None = None
        in_progress = False
        for service, action, active in reconnect_plan(self._wan_kind()):
            try:
                self.call_action(service, action)
            except FritzServiceError:
                _LOGGER.debug("Dienst %s gibt es auf dieser FRITZ!Box nicht", service)
                continue
            except FritzAuthorizationError:
                # Anmeldung an sich abgelehnt - weitere Versuche bringen nichts.
                raise
            except FritzConnectionException as err:
                code = upnp_error_code(err)
                if code == UPNP_DISCONNECT_IN_PROGRESS:
                    if active:
                        _LOGGER.info(
                            "Die FRITZ!Box trennt die Verbindung bereits (%s) - "
                            "Neuverbindung laeuft",
                            service,
                        )
                        return
                    in_progress = True
                    continue
                if (
                    code == UPNP_ALREADY_TERMINATED
                    and active
                    and self._request_connection(service)
                ):
                    return
                _LOGGER.debug("%s.%s abgelehnt: %s", service, action, err)
                if first_error is None:
                    first_error = err
                continue
            _LOGGER.debug("Neuverbindung ueber %s.%s ausgeloest", service, action)
            return
        if in_progress:
            _LOGGER.info("Die FRITZ!Box trennt die Verbindung bereits - Neuverbindung laeuft")
            return
        if first_error is not None:
            raise first_error
        raise FritzServiceError(
            "Kein WAN-Verbindungsdienst gefunden (weder TR-064 noch UPnP-IGD)"
        )

    def _request_connection(self, service: str) -> bool:
        """Baut eine bereits getrennte Verbindung neu auf; True bei Erfolg."""
        try:
            self.call_action(service, "RequestConnection")
        except FritzAuthorizationError:
            raise
        except FritzConnectionException as err:
            _LOGGER.debug("%s.RequestConnection abgelehnt: %s", service, err)
            return False
        _LOGGER.info(
            "Verbindung war bereits getrennt - Neuaufbau ueber %s angestossen", service
        )
        return True

    def reboot_repeater(self, address: str) -> None:
        """Startet einen Repeater neu (blockierend, im Executor nutzen).

        Ein Repeater im Mesh wird ueber sein EIGENES TR-064 angesprochen -
        die Hauptbox kann fremde Geraete nicht neu starten. Verwendet werden
        dieselben Zugangsdaten wie fuer die Hauptbox. Im Mesh uebernehmen
        Repeater in der Regel die Anmeldedaten der FRITZ!Box; ist das nicht
        der Fall oder ist TR-064 am Repeater aus, lehnt er die Anmeldung ab
        und der Aufrufer bekommt eine entsprechende Fehlermeldung.
        """
        data = self.entry.data
        connection = FritzConnection(
            address=address,
            user=data[CONF_USERNAME],
            password=data[CONF_PASSWORD],
            use_tls=data.get(CONF_USE_TLS, DEFAULT_USE_TLS),
            timeout=REPEATER_TIMEOUT,
        )
        connection.call_action("DeviceConfig1", "Reboot")

    @property
    def box_model(self) -> str:
        """Modellname der FRITZ!Box (leer, wenn nicht ermittelbar)."""
        try:
            return str(getattr(self.fritz_hosts.fc, "modelname", "") or "")
        except Exception:  # noqa: BLE001 - reine Anzeige, darf nie stoeren
            return ""

    # -- Mesh: alle FRITZ!-Geraete gemeinsam ------------------------------

    def _mesh_members(self, hosts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """FRITZ!Box + Repeater als Gruppe (siehe ``hosts.mesh_members``)."""
        model = self.box_model
        return mesh_members(
            hosts,
            box_name=model or "FRITZ!Box",
            box_model=model,
            box_ip=str(self.entry.data.get(CONF_HOST, "")),
        )

    def reboot_mesh(self, targets: list[dict[str, Any]]) -> dict[str, Any]:
        """Startet erst die Repeater, dann die FRITZ!Box neu (blockierend).

        Die Repeater kommen zuerst, weil sie ueber das Netz der Box angesprochen
        werden - ist die Box schon weg, erreicht der Befehl sie nicht mehr.
        Ein fehlgeschlagener Repeater haelt die uebrigen und die Box nicht auf;
        jeder Fehler wird gesammelt und dem Aufrufer gemeldet.
        """
        failed: list[dict[str, str]] = []
        for target in targets:
            name = str(target.get("name") or target.get("ip"))
            try:
                self.reboot_repeater(str(target["ip"]))
            except (FritzConnectionException, RequestException) as err:
                _LOGGER.warning("Repeater %s liess sich nicht neu starten: %s", name, err)
                failed.append({"name": name, "error": str(err)})
        if targets:
            time.sleep(MESH_REBOOT_DELAY)
        box_error: str | None = None
        try:
            self.call_action("DeviceConfig1", "Reboot")
        except (FritzConnectionException, RequestException) as err:
            _LOGGER.warning("FRITZ!Box liess sich nicht neu starten: %s", err)
            box_error = str(err)
        return {"failed": failed, "box_error": box_error}

    async def async_reboot_mesh(self) -> None:
        """Startet alle FRITZ!-Geraete neu: Repeater zuerst, die Box zuletzt."""
        members = (self.data or {}).get("mesh") or self._mesh_members(
            (self.data or {}).get("hosts", [])
        )
        targets, skipped = mesh_reboot_plan(members)
        for member in skipped:
            _LOGGER.warning(
                "Repeater %s ist nicht erreichbar (offline oder ohne IP-Adresse) "
                "und wird uebersprungen",
                member.get("name"),
            )
        result = await self.hass.async_add_executor_job(self.reboot_mesh, targets)
        if result["box_error"] is not None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="mesh_reboot_box_failed",
                translation_placeholders={
                    "error": result["box_error"],
                    "restarted": str(len(targets) - len(result["failed"])),
                },
            )
        if result["failed"]:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="mesh_reboot_partial",
                translation_placeholders={
                    "names": ", ".join(item["name"] for item in result["failed"]),
                    "error": result["failed"][0]["error"],
                },
            )

    # -- MAC-Filter und Pairing -------------------------------------------

    @property
    def pairing_until(self) -> datetime | None:
        """Zeitpunkt (UTC), zu dem der Filter wieder eingeschaltet wird, sonst None."""
        return self._pairing_until

    @property
    def pairing_minutes(self) -> int:
        """Eingestellte Dauer eines Pairings (Optionen)."""
        return int(
            self.entry.options.get(CONF_PAIRING_MINUTES, DEFAULT_PAIRING_MINUTES)
        )

    def _mac_filter_bands(self) -> list[tuple[int, dict[str, Any]]]:
        """Liest ``GetInfo`` der Baender, die den MAC-Filter tragen (blockierend)."""
        bands: list[tuple[int, dict[str, Any]]] = []
        for index in MAC_FILTER_SERVICES:
            try:
                info = self.call_action(f"WLANConfiguration{index}", "GetInfo")
            except FritzServiceError:
                continue  # dieses Band gibt es an der Box nicht
            if is_mac_filter_band(index, info):
                bands.append((index, info))
        return bands

    def _mac_filter_state(self) -> bool | None:
        """Ist der MAC-Filter an? None, wenn die Box ihn nicht anbietet (blockierend)."""
        bands = self._mac_filter_bands()
        if not bands:
            return None
        return all(as_bool(info.get(MAC_FILTER_INFO_KEY)) for _, info in bands)

    def _set_mac_filter(self, enabled: bool) -> None:
        """Schaltet den MAC-Filter und prueft das Ergebnis (blockierend).

        Geschrieben wird ueber ``WLANConfiguration.SetConfig`` - dort muessen
        alle Einstellungen mit, deshalb werden die aktuellen Werte
        zurueckgeschrieben (siehe ``hosts.set_config_arguments``). Danach wird
        neu gelesen: nimmt die Box die Aenderung nicht an, gibt es einen
        Fehler statt einer stillen Falschmeldung.
        """
        bands = self._mac_filter_bands()
        if not bands:
            raise MacFilterUnsupported("WLANConfiguration ohne MAC-Filter")
        for index, info in bands:
            if as_bool(info.get(MAC_FILTER_INFO_KEY)) == enabled:
                continue
            service = f"WLANConfiguration{index}"
            try:
                action = self.fritz_hosts.fc.services[service].actions["SetConfig"]
            except KeyError as err:
                raise MacFilterUnsupported(f"{service} kennt SetConfig nicht") from err
            input_names = [
                name
                for name, argument in action.arguments.items()
                if argument.direction == "in"
            ]
            try:
                arguments = set_config_arguments(input_names, info, enabled)
            except ValueError as err:
                raise MacFilterUnsupported(
                    f"SetConfig verlangt unbekannte Werte: {err}"
                ) from err
            self.call_action(service, "SetConfig", **arguments)
        if self._mac_filter_state() is not enabled:
            raise MacFilterNotApplied(
                "MAC-Filter steht nach dem Schreiben nicht auf "
                f"{'an' if enabled else 'aus'}"
            )

    @staticmethod
    def _mac_filter_error(err: Exception) -> HomeAssistantError:
        """Uebersetzbare Fehlermeldung zu einem gescheiterten Zugriff."""
        if isinstance(err, MacFilterUnsupported):
            key = "mac_filter_unsupported"
        elif isinstance(err, MacFilterNotApplied):
            key = "mac_filter_not_applied"
        else:
            key = "mac_filter_failed"
        return HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key=key,
            translation_placeholders={"error": str(err)},
        )

    async def async_set_mac_filter(self, enabled: bool) -> None:
        """Schaltet den MAC-Filter dauerhaft an oder aus.

        Beendet ein laufendes Pairing: ein ausdruecklicher Wunsch geht der
        Zeitschaltung vor.
        """
        try:
            await self.hass.async_add_executor_job(self._set_mac_filter, enabled)
        except (FritzConnectionException, RequestException) as err:
            raise self._mac_filter_error(err) from err
        await self._async_clear_pairing()
        await self.async_request_refresh()

    async def async_start_pairing(self, minutes: int | None = None) -> None:
        """Schaltet den MAC-Filter fuer ``minutes`` Minuten aus.

        Danach schaltet die Integration ihn von selbst wieder ein. Waehrend
        des Fensters koennen sich neue Geraete am WLAN anmelden. Der Filter
        muss dafuer eingeschaltet sein - war er ohnehin ausgeschaltet, gaebe
        es nichts zu "oeffnen", und das automatische Wiedereinschalten wuerde
        gegen den Willen des Nutzers etwas aktivieren. Laeuft schon ein
        Pairing, wird es neu gestartet (Fenster verlaengert).
        """
        minutes = int(minutes or self.pairing_minutes)
        try:
            state = await self.hass.async_add_executor_job(self._mac_filter_state)
        except (FritzConnectionException, RequestException) as err:
            raise self._mac_filter_error(err) from err
        if state is None:
            raise self._mac_filter_error(MacFilterUnsupported("kein MAC-Filter"))
        if state is False and self._pairing_until is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="pairing_filter_off"
            )

        # Erst Frist merken und Wiedereinschalten einplanen, DANN ausschalten:
        # so gibt es nie einen offenen Filter ohne hinterlegtes Ende.
        until = dt_util.utcnow() + timedelta(minutes=minutes)
        await self._pairing_store.async_save({"until": until.isoformat()})
        self._pairing_until = until
        self._async_schedule_pairing_end(until)
        if state:
            try:
                await self.hass.async_add_executor_job(self._set_mac_filter, False)
            except (FritzConnectionException, RequestException) as err:
                await self._async_clear_pairing()
                # Ist nur ein Teil der Baender umgestellt worden, den Filter
                # wieder ganz einschalten - nach bestem Wissen, ohne den
                # eigentlichen Fehler zu ueberdecken.
                try:
                    await self.hass.async_add_executor_job(self._set_mac_filter, True)
                except (FritzConnectionException, RequestException) as undo_err:
                    _LOGGER.warning(
                        "MAC-Filter konnte nach dem gescheiterten Pairing-Start "
                        "nicht sicher wieder eingeschaltet werden: %s",
                        undo_err,
                    )
                raise self._mac_filter_error(err) from err
        _LOGGER.info("Pairing gestartet: MAC-Filter aus bis %s", until.isoformat())
        self.async_update_listeners()
        await self.async_request_refresh()

    @callback
    def _async_schedule_pairing_end(self, until: datetime) -> None:
        """Plant das Wiedereinschalten (ersetzt einen vorhandenen Termin)."""
        self._async_cancel_pairing_timer()
        self._pairing_cancel = async_track_point_in_utc_time(
            self.hass, self._async_end_pairing, until
        )

    @callback
    def _async_cancel_pairing_timer(self) -> None:
        """Stoppt den geplanten Termin (aendert weder Filter noch Speicher)."""
        if self._pairing_cancel is not None:
            self._pairing_cancel()
            self._pairing_cancel = None

    async def _async_clear_pairing(self) -> None:
        """Vergisst ein laufendes Pairing samt Termin und gespeicherter Frist."""
        self._async_cancel_pairing_timer()
        if self._pairing_until is not None:
            self._pairing_until = None
            self.async_update_listeners()
        await self._pairing_store.async_remove()

    async def _async_end_pairing(self, _now: datetime | None = None) -> None:
        """Schaltet den MAC-Filter nach Ablauf des Pairings wieder ein.

        Antwortet die FRITZ!Box nicht, bleibt die Frist bestehen und es wird
        nach ``PAIRING_RETRY_SECONDS`` erneut versucht - der Filter soll nicht
        offen bleiben, nur weil die Box gerade beschaeftigt war.
        """
        self._pairing_cancel = None
        try:
            await self.hass.async_add_executor_job(self._set_mac_filter, True)
        except (FritzConnectionException, RequestException) as err:
            _LOGGER.warning(
                "MAC-Filter konnte nach dem Pairing nicht wieder eingeschaltet "
                "werden (%s) - neuer Versuch in %s s",
                err,
                PAIRING_RETRY_SECONDS,
            )
            self._pairing_cancel = async_call_later(
                self.hass, PAIRING_RETRY_SECONDS, self._async_end_pairing
            )
            return
        _LOGGER.info("Pairing beendet: MAC-Filter wieder eingeschaltet")
        await self._async_clear_pairing()
        await self.async_request_refresh()

    async def async_restore_pairing(self) -> None:
        """Nimmt ein vor dem Neustart laufendes Pairing wieder auf.

        Ist die Frist abgelaufen (Home Assistant war laenger aus), wird der
        Filter sofort wieder eingeschaltet, sonst der Termin neu geplant.
        """
        stored = await self._pairing_store.async_load()
        raw = stored.get("until") if isinstance(stored, dict) else None
        try:
            until = dt_util.parse_datetime(raw) if isinstance(raw, str) else None
        except ValueError:
            until = None
        if until is None:
            if stored:
                await self._pairing_store.async_remove()
            return
        until = dt_util.as_utc(until)
        self._pairing_until = until
        if until <= dt_util.utcnow():
            _LOGGER.info("Pairing-Frist war abgelaufen - schalte MAC-Filter wieder ein")
            await self._async_end_pairing()
        else:
            self._async_schedule_pairing_end(until)

    @callback
    def async_cancel_pairing_timer(self) -> None:
        """Beim Entladen: Termin stoppen (die gespeicherte Frist bleibt bestehen)."""
        self._async_cancel_pairing_timer()

    def _fetch_wlan(self) -> dict[str, bool]:
        """Liest den An/Aus-Zustand der vorhandenen WLAN-Baender.

        Nicht vorhandene Baender (z. B. kein 5-GHz- oder Gast-WLAN) werden
        nach dem ersten Fehlschlag nicht mehr abgefragt.
        """
        state: dict[str, bool] = {}
        mac_filter: list[bool] = []
        for index in (1, 2, 3):
            if not self._wlan_supported.get(index):
                continue
            try:
                info = self.fritz_hosts.fc.call_action(
                    f"WLANConfiguration{index}", "GetInfo"
                )
            except FritzServiceError:
                self._wlan_supported[index] = False
                continue
            except FritzConnectionException as err:
                _LOGGER.debug("WLAN %s momentan nicht abrufbar: %s", index, err)
                continue
            state[f"wlan{index}"] = bool(info.get("NewEnable"))
            if is_mac_filter_band(index, info):
                mac_filter.append(as_bool(info.get(MAC_FILTER_INFO_KEY)))
        # Filter gilt nur als "an", wenn er auf allen Hauptbaendern an ist.
        if mac_filter:
            state["mac_filter"] = all(mac_filter)
        return state

    def _fetch_connection(self) -> dict[str, Any] | None:
        """Liest die aktuellen Down-/Upload-Raten, die Leitungs-Sync-Raten
        sowie (seit 1.6.2) externe IP, Verbindungsstatus und Online-Zeit.

        Aktuelle Rate: Bytes/s (WANCommonIFC/GetAddonInfos), umgerechnet in
        kByte/s. Sync-Rate: Bit/s, umgerechnet in Mbit/s. Ohne WAN-Dienst
        wird die Abfrage dauerhaft ausgesetzt.
        """
        if not self._connection_supported:
            return None
        try:
            if self._fritz_status is None:
                self._fritz_status = FritzStatus(fc=self.fritz_hosts.fc)
            up_bytes, down_bytes = self._fritz_status.transmission_rate
            up_max_bits, down_max_bits = self._fritz_status.max_bit_rate
        except FritzServiceError:
            # Dieser FRITZ!Box fehlt der WAN-Dienst (z. B. Access-Point-Modus).
            self._connection_supported = False
            _LOGGER.info(
                "Verbindungsdaten (Down/Up) werden von dieser FRITZ!Box nicht "
                "bereitgestellt und daher nicht mehr abgefragt."
            )
            return None
        except FritzConnectionException as err:
            _LOGGER.debug("Verbindungsdaten momentan nicht abrufbar: %s", err)
            return None
        return {
            "down_rate": to_kbytes_per_s(down_bytes),
            "up_rate": to_kbytes_per_s(up_bytes),
            "down_max": to_mbit_per_s(down_max_bits),
            "up_max": to_mbit_per_s(up_max_bits),
            "external_ip": self._fetch_external_ip(),
            "online": self._fetch_is_connected(),
            "uptime": self._fetch_connection_uptime(),
        }

    def _fetch_external_ip(self) -> str | None:
        """Aktuelle oeffentliche IPv4-Adresse, oder ``None`` bei Fehler.

        Eigener, einzeln abgesicherter Aufruf: faellt er aus (z. B. DS-Lite
        ohne eigene IPv4, oder eine Box, die das trotz WAN-Dienst nicht
        meldet), sollen Down-/Upload-Raten davon unberuehrt bleiben.
        """
        try:
            ip = str(self._fritz_status.external_ip or "").strip()
        except (FritzConnectionException, RequestException) as err:
            _LOGGER.debug("Externe IP momentan nicht abrufbar: %s", err)
            return None
        return ip or None

    def _fetch_is_connected(self) -> bool | None:
        """Ob die FRITZ!Box aktuell eine Internetverbindung aufgebaut hat."""
        try:
            return bool(self._fritz_status.is_connected)
        except (FritzConnectionException, RequestException) as err:
            _LOGGER.debug("Verbindungsstatus momentan nicht abrufbar: %s", err)
            return None

    def _fetch_connection_uptime(self) -> int | None:
        """Dauer der aktuellen Internetverbindung in Sekunden.

        Bewusst ``WANIPConn``-``GetStatusInfo`` (Verbindungs-Uptime) statt
        ``DeviceInfo1``-``GetInfo`` (Geraete-Uptime): Letzteres lehnen manche
        Boxen (beobachtet: FRITZ!Box 5690 Pro) mit HTTP 401 ab, siehe
        ``config_flow.py``. Die Verbindungs-Uptime kommt ueber denselben
        Dienst, der fuer die Down-/Upload-Raten bereits funktioniert.
        """
        try:
            uptime = int(self._fritz_status.connection_uptime)
        except (FritzConnectionException, RequestException, TypeError, ValueError) as err:
            _LOGGER.debug("Online-Zeit momentan nicht abrufbar: %s", err)
            return None
        return uptime if uptime >= 0 else None

    def _ha_device_map(self) -> dict[str, dict[str, str]]:
        """Bildet MAC-Adressen auf Home-Assistant-Geraete ab.

        Grundlage ist die Geraeteregistrierung. Zugeordnet wird ueber die
        MAC-Adresse - primaer aus Verbindungen vom Typ ``mac``. Zusaetzlich
        werden MAC-artige Werte aus anderen Verbindungstypen und aus den
        Identifiern beruecksichtigt, weil manche Integrationen die MAC dort
        ablegen. Erkannt wird nur, was eindeutig wie eine 12-stellige
        MAC-Adresse aussieht; es wird nichts geraten.

        Auch deaktivierte Geraete werden beruecksichtigt: sie tragen
        weiterhin Name und ID und sollen in der Karte erscheinen.

        Grenze: Findet sich zu einem Geraet ueberhaupt keine MAC in der
        Registry (z. B. weil eine Integration die MAC nicht eintraegt -
        bei manchen Matter-Geraeten der Fall), kann es nicht zugeordnet
        werden. Das liegt an der jeweiligen Quell-Integration, nicht hier.
        """
        registry = dr.async_get(self.hass)
        mapping: dict[str, dict[str, str]] = {}

        def _add(raw_value: str, device: dr.DeviceEntry) -> None:
            key = mac_key(raw_value)
            # Nur echte 12-stellige MACs; die Null-MAC (00:00:...) taugt
            # laut IEEE nicht als Kennung und wird verworfen.
            if len(key) != 12 or key == "000000000000":
                return
            if key in mapping:
                return
            mapping[key] = {
                "name": device.name_by_user or device.name or "",
                "device_id": device.id,
                "area": device.area_id or "",
            }

        def _string_parts(item):
            """Liefert alle String-Elemente eines Tupels/einer Liste.

            Verbindungen und Identifier sind laut Spezifikation 2-Tupel, doch
            nicht jede Integration haelt sich daran: manche legen z. B. Identifier
            als 3-Tupel an. Festes Entpacken (``a, b = item``) wuerde dann
            abstuerzen. Deshalb wird hier ohne Annahme ueber die Laenge
            gearbeitet - jedes String-Element kommt als MAC-Kandidat in Frage,
            und ``_add`` verwirft alles, was keine echte MAC ist.
            """
            if isinstance(item, (tuple, list)):
                for element in item:
                    if isinstance(element, str):
                        yield element
            elif isinstance(item, str):
                yield item

        # Geraete dieser Integration (die Repeater) kommen zuletzt an die
        # Reihe: hat dieselbe MAC-Adresse auch ein Geraet einer anderen
        # Integration, gewinnt dieses wie bisher. So aendert das Anlegen der
        # Repeater-Geraete nichts an der bisherigen Zuordnung.
        own_entry_id = self.entry.entry_id

        def _is_own(device: dr.DeviceEntry) -> bool:
            # Neuere Home-Assistant-Staende fuehren ein Geraet nur noch unter
            # EINEM Eintrag (``config_entry_id``); ``config_entries`` ist dort
            # nur noch eine Kompatibilitaetshilfe. Aeltere kennen nur Letzteres.
            entry_id = getattr(device, "config_entry_id", None)
            if entry_id is not None:
                return entry_id == own_entry_id
            return own_entry_id in device.config_entries

        def _is_own_host_device(device: dr.DeviceEntry) -> bool:
            # Die von dieser Integration selbst angelegten Netzwerkgeraete
            # (Option "Netzwerkgeraete als Geraete", Idee 9) tragen dieselbe MAC
            # wie der Host - sie als "Home-Assistant-Geraet" zu melden waere
            # ein Selbstverweis und wuerde die Spalte "Home Assistant" fuellen,
            # ohne dass ein anderes Geraet dahintersteht.
            prefix = f"{own_entry_id}_host_"
            return any(
                isinstance(item, str) and item.startswith(prefix)
                for identifier in device.identifiers
                for item in _string_parts(identifier)
            )

        devices = sorted(
            (d for d in self._iter_devices(registry) if not _is_own_host_device(d)),
            key=_is_own,
        )
        for device in devices:
            # 1) Verbindungen vom Typ "mac" haben Vorrang. Nur bei einem
            #    sauberen 2-Tupel wird der Typ geprueft.
            for connection in device.connections:
                if (
                    isinstance(connection, (tuple, list))
                    and len(connection) == 2
                    and connection[0] == dr.CONNECTION_NETWORK_MAC
                ):
                    _add(connection[1], device)
            # 2) Alle MAC-artigen Werte aus Verbindungen und Identifiern -
            #    tolerant gegenueber abweichenden Tupellaengen.
            for connection in device.connections:
                for value in _string_parts(connection):
                    _add(value, device)
            for identifier in device.identifiers:
                for value in _string_parts(identifier):
                    _add(value, device)
        return mapping

    @staticmethod
    def _iter_devices(registry: dr.DeviceRegistry):
        """Iteriert die Geraete-Eintraege der Registry versionsuebergreifend.

        Seit Home Assistant 2026.9 liefert ``for x in registry.devices`` direkt
        die ``DeviceEntry``-Objekte; auf aelteren Versionen liefert dieselbe
        Iteration die Schluessel (Geraete-IDs als Strings). ``.values()`` waere
        auf neuen Versionen wiederum als veraltet markiert. Daher wird hier
        iteriert und ein String-Schluessel ueber die unterstuetzte Methode
        ``async_get`` in seinen Eintrag aufgeloest - das funktioniert auf allen
        Versionen ohne Absturz und ohne Deprecation-Warnung.
        """
        for item in registry.devices:
            device = item if not isinstance(item, str) else registry.async_get(item)
            if device is not None:
                yield device

    async def _async_update_data(self) -> dict[str, Any]:
        """Holt die Geraeteliste und reichert sie an."""
        # Im Hintergrund, damit eine langsame Antwort von GitHub weder den Start noch
        # die Aktualisierung der Geraeteliste aufhaelt (Ergebnis erscheint beim naechsten Zyklus).
        if self.check_updates and self._version_due():
            self.entry.async_create_background_task(
                self.hass, self._async_check_version(), "fritzbox_netzwerk_version_check"
            )
        if self._block_until:
            await self._async_release_due_blocks()
        if self._profile_revert:
            await self._async_release_due_profiles()
        try:
            raw_hosts, refreshed, connection, wlan, bands, mesh_links = (
                await self.hass.async_add_executor_job(self._fetch)
            )
        except (FritzSecurityError, FritzAuthorizationError) as err:
            # Die Box lehnt Anmeldungen gelegentlich kurzzeitig ab, obwohl die
            # Zugangsdaten stimmen (Neustart, Update, parallele Anmeldungen).
            # Erst mehrere Ablehnungen in Folge verlangen eine neue Anmeldung.
            count, give_up = self._auth_guard.failure(self.entry.entry_id)
            if give_up:
                raise ConfigEntryAuthFailed(
                    "Die FRITZ!Box lehnt die Anmeldung wiederholt ab. Bitte Benutzername "
                    "und Kennwort pruefen; das Konto braucht die Berechtigung "
                    "'FRITZ!Box Einstellungen'."
                ) from err
            _LOGGER.warning(
                "Die FRITZ!Box hat die Anmeldung abgelehnt (%s) - Versuch %s von %s, "
                "es wird erneut versucht",
                err,
                count,
                AUTH_FAILURE_LIMIT,
            )
            raise UpdateFailed(
                f"Anmeldung voruebergehend abgelehnt (Versuch {count} von "
                f"{AUTH_FAILURE_LIMIT}): {err}"
            ) from err
        except FritzServiceError as err:
            raise UpdateFailed(
                "Der Dienst 'Hosts' ist auf dieser FRITZ!Box nicht verfuegbar. "
                "Ist 'Zugriff fuer Anwendungen zulassen' aktiviert?"
            ) from err
        except FritzConnectionException as err:
            raise UpdateFailed(f"Abruf der Geraeteliste fehlgeschlagen: {err}") from err

        # Abruf gelungen: fruehere Ablehnungen waren nur vorubergehend.
        self._auth_guard.success(self.entry.entry_id)

        if refreshed:
            self._address_source_scan = dt_util.utcnow()

        # Fuer "Neues Geraet"/"zum ersten Mal gesehen" wird der Stand VOR
        # dieser Aktualisierung gebraucht - danach steht jedes aktive Geraet
        # bereits in ``self._last_seen`` und waere nicht mehr von "schon
        # bekannt" zu unterscheiden. Beim allerersten Abruf nach der
        # Einrichtung (Baseline) wird beides uebersprungen, sonst waere das
        # komplette vorhandene Heimnetz "neu".
        known_before = set(self._last_seen.keys())
        self._update_last_seen(raw_hosts)
        is_baseline_cycle = self._new_device_baseline_pending
        self._new_device_baseline_pending = False
        if not is_baseline_cycle:
            self._update_first_seen(raw_hosts, known_before)

        hosts = build_hosts(
            raw_hosts,
            self._address_sources if self.track_address_source else None,
            self._ha_device_map(),
            self._last_seen,
            self._dhcp_pool if self.track_address_source else None,
            self._oui,
            bands,
            self._first_seen,
            mesh_links,
            self._notes,
        )
        # Fuer den NAECHSTEN Zyklus: ob sich eine Mesh-Topologie-Abfrage
        # ueberhaupt lohnt (siehe ``_fetch``/``_fetch_mesh_topology``).
        self._repeater_seen = any(
            is_repeater(str(raw.get("X_AVM-DE_Model") or "")) for raw in raw_hosts
        )

        if not is_baseline_cycle:
            self._notify_new_devices(hosts, known_before)
        self._notify_external_ip_change(connection)

        return {
            "hosts": hosts,
            "mesh": self._mesh_members(hosts),
            "summary": summarize(hosts),
            "connection": connection,
            "wlan": wlan,
            "last_scan": dt_util.utcnow().isoformat(),
            "address_source_scan": (
                self._address_source_scan.isoformat()
                if self._address_source_scan
                else None
            ),
            "track_address_source": self.track_address_source,
            "system": self._system_stats,
            "version": self.version_info,
        }

    # -- Hersteller (OUI) -------------------------------------------------

    @property
    def user_data_dir(self) -> str:
        """Ordner fuer Dateien, die ein HACS-Update nicht ueberschreibt."""
        return self.hass.config.path(USER_DATA_DIRNAME)

    def _read_oui_layers(self) -> tuple[dict[str, str], dict[str, int]]:
        """Liest Basisliste, heruntergeladene Aktualisierung und eigene Zuordnungen.

        Reihenfolge der Vorrangs: mitgelieferte Liste < heruntergeladene
        Aktualisierung < eigene Zuordnungen. Nur die Basisliste ist
        Pflicht; fehlen die anderen oder sind sie kaputt, bleibt die
        Integration unberuehrt (blockierend, im Executor aufrufen).
        """
        stats: dict[str, int] = {}
        base = load_oui(OUI_FILE)
        stats["basis"] = len(base)

        update: dict[str, str] = {}
        update_path = os.path.join(self.user_data_dir, OUI_UPDATE_FILENAME)
        if os.path.isfile(update_path):
            try:
                update = load_oui(update_path)
            except OSError as err:
                _LOGGER.warning("Aktualisierte Herstellerliste %s nicht lesbar: %s", update_path, err)
        stats["aktualisierung"] = len(update)

        custom: dict[str, str] = {}
        custom_path = os.path.join(self.user_data_dir, OUI_CUSTOM_FILENAME)
        if os.path.isfile(custom_path):
            try:
                with open(custom_path, encoding="utf-8", errors="replace") as handle:
                    lines = handle.read().splitlines()
                custom = parse_oui(lines)
                bad = validate_custom_oui_lines(lines)
                if bad:
                    _LOGGER.warning(
                        "%s: Zeile(n) %s ignoriert - erwartet wird PRAEFIX:Name "
                        "(6, 7 oder 9 Hex-Zeichen)",
                        custom_path,
                        ", ".join(str(n) for n in bad[:10]),
                    )
            except OSError as err:
                _LOGGER.warning("Eigene Herstellerzuordnung %s nicht lesbar: %s", custom_path, err)
        stats["eigene"] = len(custom)
        return merge_oui(base, update, custom), stats

    def _ensure_custom_oui_template(self) -> None:
        """Legt eine kommentierte, leere Datei fuer eigene Zuordnungen an (einmalig)."""
        path = os.path.join(self.user_data_dir, OUI_CUSTOM_FILENAME)
        if os.path.exists(path):
            return
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            with open(path, "x", encoding="utf-8") as handle:
                handle.write(
                    "# Eigene Herstellerzuordnungen fuer fritzbox_netzwerk.\n"
                    "# Eine Zeile je Eintrag: PRAEFIX:Name, z. B.\n"
                    "#   A1B2C3:Mein Bastelgeraet\n"
                    "#   A1B2C3D:Prototyp (7 Zeichen = MA-M)\n"
                    "#   A1B2C3D4E:Prototyp (9 Zeichen = MA-S)\n"
                    "# Diese Datei hat Vorrang vor der mitgelieferten und der aktualisierten\n"
                    "# Liste und wird von Updates NICHT ueberschrieben. Aenderungen gelten\n"
                    "# nach einem Neustart oder nach dem Dienst fritzbox_netzwerk.update_oui.\n"
                )
        except FileExistsError:
            return
        except OSError as err:
            _LOGGER.debug("Vorlage %s nicht angelegt: %s", path, err)

    async def async_load_oui(self) -> None:
        """Laedt die Herstellertabelle (im Executor, einmalig beim Start).

        Ein Fehler beim Lesen ist kein Grund, die Integration scheitern zu
        lassen: ohne Tabelle fehlt nur die Spalte "Hersteller".
        """
        try:
            await self.hass.async_add_executor_job(self._ensure_custom_oui_template)
            self._oui, self.oui_stats = await self.hass.async_add_executor_job(
                self._read_oui_layers
            )
        except OSError as err:
            _LOGGER.warning("Herstellertabelle %s nicht lesbar: %s", OUI_FILE, err)
            self._oui = {}
            self.oui_stats = {}
            return
        _LOGGER.debug("Herstellertabelle geladen: %s Eintraege (%s)", len(self._oui), self.oui_stats)

    def _write_oui_update(self, table: dict[str, str]) -> None:
        """Schreibt die heruntergeladene Liste atomar (erst temporaer, dann ersetzen)."""
        os.makedirs(self.user_data_dir, exist_ok=True)
        target = os.path.join(self.user_data_dir, OUI_UPDATE_FILENAME)
        header = (
            "fritzbox_netzwerk - Herstellerliste (IEEE MA-L, MA-M, MA-S)\n"
            f"Abgerufen: {dt_util.utcnow().isoformat()}\n"
            "Wird vom Dienst fritzbox_netzwerk.update_oui erzeugt - nicht von Hand aendern,\n"
            "eigene Zuordnungen gehoeren in oui_custom.txt."
        )
        fd, tmp = tempfile.mkstemp(dir=self.user_data_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(serialize_oui(table, header))
            os.replace(tmp, target)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    async def async_update_oui(self) -> dict[str, Any]:
        """Holt die IEEE-Register, speichert sie und laedt die Tabelle neu.

        Die bisherige Liste bleibt unangetastet, solange nicht alle drei
        Register vollstaendig und plausibel heruntergeladen wurden (siehe
        ``MIN_MA_L_ENTRIES``). Gilt fuer ALLE eingerichteten FRITZ!Boxen, da
        die Datei gemeinsam genutzt wird.
        """
        if self._oui_update_lock.locked():
            raise HomeAssistantError("Die Herstellerliste wird gerade schon aktualisiert.")
        async with self._oui_update_lock:
            session = async_get_clientsession(self.hass)
            tables: dict[str, dict[str, str]] = {}
            for name, url, length in IEEE_REGISTER_URLS:
                try:
                    async with asyncio.timeout(90):
                        response = await session.get(url)
                        if response.status != 200:
                            raise HomeAssistantError(
                                f"IEEE-Register {name} nicht abrufbar (HTTP {response.status})."
                            )
                        text = await response.text(errors="replace")
                except HomeAssistantError:
                    raise
                except (TimeoutError, OSError, asyncio.CancelledError) as err:
                    if isinstance(err, asyncio.CancelledError):
                        raise
                    raise HomeAssistantError(
                        f"IEEE-Register {name} nicht abrufbar: {err or 'Zeitueberschreitung'}"
                    ) from err
                except Exception as err:  # noqa: BLE001 - aiohttp-Fehler gesammelt melden
                    raise HomeAssistantError(f"IEEE-Register {name} nicht abrufbar: {err}") from err
                tables[name] = await self.hass.async_add_executor_job(parse_ieee_csv, text, length)

            if len(tables["MA-L"]) < MIN_MA_L_ENTRIES:
                raise HomeAssistantError(
                    f"Das heruntergeladene MA-L-Register enthaelt nur {len(tables['MA-L'])} "
                    f"Eintraege (erwartet mindestens {MIN_MA_L_ENTRIES}) - die bisherige "
                    "Liste bleibt unveraendert."
                )
            merged = merge_oui(tables["MA-L"], tables["MA-M"], tables["MA-S"])
            await self.hass.async_add_executor_job(self._write_oui_update, merged)

        result = {name: len(table) for name, table in tables.items()}
        for entry in self.hass.config_entries.async_loaded_entries(DOMAIN):
            other = entry.runtime_data
            await other.async_load_oui()
            await other.async_request_refresh()
        return result

    # -- Internetzugang sperren (optional mit Frist, Idee 22) ---------------

    def _host_ip(self, key: str) -> str:
        for host in (self.data or {}).get("hosts", []):
            if mac_key(host.get("mac")) == key:
                return str(host.get("ip") or "")
        return ""

    async def async_set_internet_access(
        self, mac: str, blocked: bool, minutes: int | None = None
    ) -> None:
        """Sperrt oder erlaubt den Internetzugang eines Geraets.

        Die FRITZ!Box-Aktion arbeitet mit der IPv4-Adresse, die sich per DHCP
        aendern kann - deshalb wird sie hier aus der aktuellen Hostliste ueber
        den stabilen MAC-Schluessel aufgeloest. Mit ``minutes`` wird die Sperre
        nach der Frist automatisch wieder aufgehoben (gespeichert, ueberlebt
        einen Neustart; geprueft wird im Abfrageintervall, die Genauigkeit
        entspricht also diesem Intervall).
        """
        key = mac_key(mac)
        if len(key) != 12:
            raise HomeAssistantError(f"Ungueltige MAC-Adresse: {mac}")
        ip = self._host_ip(key)
        if not ip:
            raise HomeAssistantError(
                f"Zu {mac} ist derzeit keine IP-Adresse bekannt - ist das Geraet "
                "der FRITZ!Box bekannt und hat es eine IPv4-Adresse?"
            )

        def _set() -> None:
            self.fritz_hosts.fc.call_action(
                "X_AVM-DE_HostFilter1",
                "DisallowWANAccessByIP",
                NewIPv4Address=ip,
                NewDisallow=blocked,
            )

        try:
            await self.hass.async_add_executor_job(_set)
        except FritzServiceError as err:
            raise HomeAssistantError(
                "Diese FRITZ!Box stellt das Sperren des Internetzugangs ueber "
                "TR-064 nicht bereit (Dienst X_AVM-DE_HostFilter fehlt)."
            ) from err
        except FritzConnectionException as err:
            raise HomeAssistantError(
                f"Internetzugang fuer {mac} ({ip}) konnte nicht geaendert werden: {err}"
            ) from err

        if blocked and minutes:
            until = dt_util.utcnow() + timedelta(minutes=int(minutes))
            self._block_until[key] = until.isoformat()
        else:
            self._block_until.pop(key, None)
        self._block_store.async_delay_save(lambda: dict(self._block_until), 1)
        await self.async_request_refresh()

    async def async_load_blocks(self) -> None:
        """Laedt gespeicherte Sperren mit Frist beim Start (kaputte Eintraege entfallen)."""
        stored = await self._block_store.async_load()
        self._block_until = {}
        if isinstance(stored, dict):
            for key, raw in stored.items():
                try:
                    parsed = dt_util.parse_datetime(str(raw))
                except ValueError:
                    parsed = None
                if parsed is not None and len(str(key)) == 12:
                    self._block_until[str(key)] = dt_util.as_utc(parsed).isoformat()

    async def _async_release_due_blocks(self) -> None:
        """Hebt Sperren auf, deren Frist abgelaufen ist (best effort)."""
        now = dt_util.utcnow()
        for key, raw in list(self._block_until.items()):
            until = dt_util.parse_datetime(raw)
            if until is None or dt_util.as_utc(until) > now:
                continue
            try:
                await self.async_set_internet_access(key, False)
                _LOGGER.info("Internetsperre fuer %s abgelaufen - Zugang freigegeben", key)
            except HomeAssistantError as err:
                # Beim naechsten Zyklus erneut versuchen (z. B. Geraet kurz ohne IP).
                _LOGGER.warning("Sperre fuer %s konnte nicht aufgehoben werden: %s", key, err)

    @property
    def blocked_until(self) -> dict[str, str]:
        """Aktive Sperren mit Frist (MAC-Schluessel -> Ende, ISO-UTC)."""
        return dict(self._block_until)

    # -- Versionspruefung und Blueprints -------------------------------------

    @property
    def check_updates(self) -> bool:
        """Ob einmal taeglich bei GitHub nach einer neuen Version gefragt wird."""
        return bool(self.entry.options.get(CONF_CHECK_UPDATES, DEFAULT_CHECK_UPDATES))

    @property
    def version_info(self) -> dict[str, Any]:
        """Installierte und (falls bekannt) neueste Version fuer Sensor und Karte."""
        checked = self._version_checked.isoformat() if self._version_checked else None
        return build_version_info(VERSION, self._latest_release, checked)

    def _version_due(self) -> bool:
        """Ob die taegliche Versionspruefung faellig ist."""
        if self._version_checked is None:
            return True
        return dt_util.utcnow() - self._version_checked >= timedelta(hours=UPDATE_CHECK_HOURS)

    async def _async_check_version(self) -> None:
        """Fragt hoechstens alle ``UPDATE_CHECK_HOURS`` Stunden bei GitHub nach.

        Jeder Fehler ist harmlos: es bleibt beim zuletzt bekannten Stand und
        der naechste Versuch folgt erst nach der Wartezeit (kein Dauerbeschuss).
        """
        if not self.check_updates:
            return
        now = dt_util.utcnow()
        if self._version_checked and now - self._version_checked < timedelta(hours=UPDATE_CHECK_HOURS):
            return
        self._version_checked = now
        try:
            session = async_get_clientsession(self.hass)
            async with asyncio.timeout(10):
                response = await session.get(
                    GITHUB_LATEST_RELEASE_URL,
                    headers={
                        "Accept": "application/vnd.github+json",
                        "User-Agent": f"fritzbox_netzwerk/{VERSION}",
                    },
                )
                if response.status != 200:
                    _LOGGER.debug("Versionspruefung: HTTP %s", response.status)
                    return
                payload = await response.json(content_type=None)
        except (TimeoutError, OSError, ValueError) as err:
            _LOGGER.debug("Versionspruefung nicht moeglich: %s", err)
            return
        except Exception as err:  # noqa: BLE001 - aiohttp-Fehler duerfen nie die Abfrage stoeren
            _LOGGER.debug("Versionspruefung fehlgeschlagen: %s", err)
            return
        release = parse_release(payload)
        if release:
            self._latest_release = release

    async def async_install_blueprints(self, overwrite: bool = False) -> dict[str, Any]:
        """Kopiert die mitgelieferten Blueprints in ``<config>/blueprints`` (auf Anforderung)."""
        source = os.path.join(os.path.dirname(__file__), BLUEPRINTS_DIRNAME)
        target = self.hass.config.path(BLUEPRINTS_DIRNAME)
        try:
            return await self.hass.async_add_executor_job(
                install_blueprints, source, target, overwrite
            )
        except OSError as err:
            raise HomeAssistantError(f"Blueprints konnten nicht kopiert werden: {err}") from err

    # -- Kindersicherung: Zugangsprofile (Idee 22, experimentell) ---------

    @property
    def parental_enabled(self) -> bool:
        """Ob die Zugangsprofil-Funktionen (Weboberflaeche) freigeschaltet sind."""
        return bool(self.entry.options.get(CONF_ENABLE_PARENTAL, DEFAULT_ENABLE_PARENTAL))

    @property
    def profile_reverts(self) -> dict[str, dict[str, str]]:
        """Laufende zeitlich begrenzte Profilwechsel (Diagnose)."""
        return {key: dict(value) for key, value in self._profile_revert.items()}

    async def _async_web(self, func: Callable[..., Any], *args: Any) -> Any:
        """Wie ``_run_web`` im Executor; Fehler werden zu ``HomeAssistantError``."""
        if not self.parental_enabled:
            raise HomeAssistantError(
                "Die Zugangsprofil-Funktionen sind aus - in den Optionen "
                "'Zugangsprofile der Kindersicherung steuern (experimentell)' einschalten."
            )
        try:
            return await self.hass.async_add_executor_job(self._run_web, func, *args)
        except (ValueError, RequestException) as err:
            raise HomeAssistantError(f"Zugangsprofile: {err}") from err

    async def async_list_access_profiles(self) -> list[dict[str, str]]:
        """Alle Zugangsprofile der Box (``id``, ``name``)."""
        return await self._async_web(list_profiles)

    async def async_get_access_profile(self, mac: str) -> dict[str, Any]:
        """Aktuelles Zugangsprofil eines Geraets."""
        result = await self._async_web(get_device_profile, mac)
        pending = self._profile_revert.get(mac_key(mac))
        return {**result, "zurueck_auf": pending.get("profile") if pending else None,
                "zurueck_um": pending.get("until") if pending else None}

    async def async_set_access_profile(
        self, mac: str, profile: str, minutes: int | None = None
    ) -> dict[str, Any]:
        """Weist einem Geraet ein Zugangsprofil zu, optional nur fuer ``minutes``.

        Mit Frist wird nach Ablauf das urspruengliche Profil wiederhergestellt
        (gespeichert, ueberlebt einen Neustart; geprueft im Abfrageintervall).
        Ein zweiter zeitlich begrenzter Wechsel merkt sich weiterhin das
        ERSTE Profil, nicht das gerade gesetzte voruebergehende.
        """
        key = mac_key(mac)
        if len(key) != 12:
            raise HomeAssistantError(f"Ungueltige MAC-Adresse: {mac}")
        result = await self._async_web(assign_profile, mac, profile)
        if minutes:
            pending = self._profile_revert.get(key)
            original = pending["profile"] if pending else result["previous"]
            if original and original != result["profile"]:
                until = dt_util.utcnow() + timedelta(minutes=int(minutes))
                self._profile_revert[key] = {"profile": original, "until": until.isoformat()}
            else:
                self._profile_revert.pop(key, None)
        else:
            self._profile_revert.pop(key, None)
        self._profile_store.async_delay_save(lambda: dict(self._profile_revert), 1)
        return result

    async def async_load_profile_reverts(self) -> None:
        """Laedt gespeicherte Profil-Fristen beim Start (kaputte Eintraege entfallen)."""
        stored = await self._profile_store.async_load()
        self._profile_revert = {}
        if isinstance(stored, dict):
            for key, value in stored.items():
                if not isinstance(value, dict) or len(str(key)) != 12:
                    continue
                profile = str(value.get("profile") or "")
                try:
                    until = dt_util.parse_datetime(str(value.get("until") or ""))
                except ValueError:
                    until = None
                if profile.startswith("filtprof") and until is not None:
                    self._profile_revert[str(key)] = {
                        "profile": profile,
                        "until": dt_util.as_utc(until).isoformat(),
                    }

    async def _async_release_due_profiles(self) -> None:
        """Stellt Profile wieder her, deren Frist abgelaufen ist (best effort)."""
        now = dt_util.utcnow()
        for key, value in list(self._profile_revert.items()):
            until = dt_util.parse_datetime(value.get("until", ""))
            if until is None or dt_util.as_utc(until) > now:
                continue
            try:
                await self._async_web(assign_profile, key, value["profile"])
            except HomeAssistantError as err:
                # Beim naechsten Zyklus erneut versuchen.
                _LOGGER.warning("Zugangsprofil fuer %s nicht zurueckgesetzt: %s", key, err)
                continue
            _LOGGER.info("Zugangsprofil fuer %s nach Ablauf wiederhergestellt", key)
            self._profile_revert.pop(key, None)
            self._profile_store.async_delay_save(lambda: dict(self._profile_revert), 1)

    # -- Notizen und Etiketten --------------------------------------------

    async def async_load_notes(self) -> None:
        """Laedt die gespeicherten Notizen/Etiketten beim Start."""
        self._notes = load_notes(await self._notes_store.async_load())

    async def async_set_note(
        self,
        mac: str,
        label: Any = None,
        note: Any = None,
        reserved: Any = None,
    ) -> dict[str, Any] | None:
        """Setzt Etikett, Notiz und "reserviert" eines Geraets (alles leer = loeschen).

        Nicht uebergebene Felder (``None``) bleiben unveraendert. Die
        Hostliste wird sofort angepasst (ohne neue Abfrage an der Box).
        """
        key = mac_key(mac)
        if len(key) != 12:
            raise HomeAssistantError(f"Ungueltige MAC-Adresse: {mac}")
        current = self._notes.get(key, {})
        entry = make_note_entry(
            current.get("label") if label is None else label,
            current.get("note") if note is None else note,
            current.get("reserved") if reserved is None else reserved,
        )
        if entry:
            self._notes[key] = entry
        else:
            self._notes.pop(key, None)
        self._notes_store.async_delay_save(lambda: dict(self._notes), 1)

        if self.data:
            pool = self._dhcp_pool if self.track_address_source else None
            hosts = self.data.get("hosts", [])
            for host in hosts:
                if mac_key(host.get("mac")) != key:
                    continue
                host["label"] = (entry or {}).get("label", "")
                host["note"] = (entry or {}).get("note", "")
                host["reserved"] = bool((entry or {}).get("reserved"))
                host["ip_class"] = classify_ip_with_reserved(host, pool)
            self.async_set_updated_data(
                {**self.data, "hosts": hosts, "summary": summarize(hosts)}
            )
        return entry

    # -- "Zuletzt gesehen" ------------------------------------------------

    async def async_load_last_seen(self) -> None:
        """Laedt die gespeicherten 'zuletzt gesehen'-Zeitstempel beim Start."""
        stored = await self._last_seen_store.async_load()
        if isinstance(stored, dict):
            self._last_seen = {
                str(key): str(value) for key, value in stored.items() if value
            }
        # Keine gespeicherten Daten: entweder eine ganz neue Einrichtung oder
        # der erste Start nach einem Update von einer Version ohne dieses
        # Feature. Der erste Abruf merkt sich dann nur die Ausgangslage,
        # statt das gesamte vorhandene Heimnetz als "neues Geraet" zu melden.
        self._new_device_baseline_pending = not self._last_seen

    async def async_load_first_seen(self) -> None:
        """Laedt die gespeicherten 'zum ersten Mal gesehen'-Zeitstempel beim Start."""
        stored = await self._first_seen_store.async_load()
        if isinstance(stored, dict):
            self._first_seen = {
                str(key): str(value) for key, value in stored.items() if value
            }

    def _update_last_seen(self, raw_hosts: list[dict[str, Any]]) -> None:
        """Schreibt fuer jedes aktuell aktive Geraet den Zeitpunkt mit.

        Nur aktive Geraete werden aktualisiert; inaktive behalten ihren
        letzten bekannten Wert. Geaendert wird nur bei tatsaechlicher
        Aenderung, danach wird verzoegert gespeichert (die Store-Helfer
        buendeln haeufige Schreibvorgaenge selbst).
        """
        now = dt_util.utcnow().isoformat()
        changed = False
        for raw in raw_hosts or []:
            if not raw.get("Active"):
                continue
            key = mac_key(raw.get("MACAddress"))
            if not key:
                continue
            self._last_seen[key] = now
            changed = True
        if changed:
            self._last_seen_store.async_delay_save(lambda: dict(self._last_seen), 5)

    @callback
    def async_add_new_device_listener(
        self, listener: Callable[[dict[str, Any]], None]
    ) -> CALLBACK_TYPE:
        """Meldet einen Listener fuer neu auftauchende Geraete an (Event-Entitaet).

        Liefert eine Funktion zum Abmelden, wie bei
        ``DataUpdateCoordinator.async_add_listener``.
        """
        self._new_device_listeners.append(listener)

        @callback
        def _remove() -> None:
            self._new_device_listeners.remove(listener)

        return _remove

    def _update_first_seen(
        self, raw_hosts: list[dict[str, Any]], known_before: set[str]
    ) -> None:
        """Schreibt fuer neu auftauchende Geraete den 'zum ersten Mal gesehen'-Zeitstempel.

        Laeuft - wie ``_update_last_seen`` - direkt auf den rohen TR-064-
        Datensaetzen und VOR ``build_hosts()``, damit der Zeitstempel schon
        im selben Zyklus in der Hostliste/im Karten-Filter "Neu (letzte 7
        Tage)" ankommt, statt erst einen Abrufzyklus spaeter. Nur fuer
        Geraete, die hier echt neu sind (siehe ``hosts.apply_first_seen``
        fuer die Begruendung); Aufruf wird vom Aufrufer uebersprungen, wenn
        gerade die Baseline nach der Einrichtung gilt.
        """
        now = dt_util.utcnow().isoformat()
        changed = False
        for raw in raw_hosts or []:
            if not raw.get("Active"):
                continue
            key = mac_key(raw.get("MACAddress"))
            if not key or key in known_before or key in self._first_seen:
                continue
            self._first_seen[key] = now
            changed = True
        if changed:
            self._first_seen_store.async_delay_save(lambda: dict(self._first_seen), 5)

    def _notify_new_devices(
        self, hosts: list[dict[str, Any]], known_before: set[str]
    ) -> None:
        """Meldet jedes seit dem letzten Abruf neu aufgetauchte Geraet.

        "Neu" heisst: aktiv UND noch nie zuvor in ``self._last_seen``
        verzeichnet. Wird vom Aufrufer uebersprungen, wenn gerade die
        Baseline nach der Einrichtung gilt (siehe ``async_load_last_seen``) -
        sonst waere beim ersten Start das komplette vorhandene Heimnetz
        "neu".
        """
        if not self._new_device_listeners:
            return
        for host in hosts:
            if not host.get("active"):
                continue
            key = mac_key(host.get("mac"))
            if not key or key in known_before:
                continue
            for listener in list(self._new_device_listeners):
                try:
                    listener(host)
                except Exception:  # noqa: BLE001 - ein Listener darf den Abruf nie stoppen
                    _LOGGER.exception("Fehler im 'Neues Geraet'-Listener")

    @callback
    def async_add_external_ip_listener(
        self, listener: Callable[[str, str], None]
    ) -> CALLBACK_TYPE:
        """Meldet einen Listener fuer eine geaenderte externe IP an."""
        self._external_ip_listeners.append(listener)

        @callback
        def _remove() -> None:
            self._external_ip_listeners.remove(listener)

        return _remove

    def _notify_external_ip_change(self, connection: dict[str, Any] | None) -> None:
        """Meldet eine geaenderte externe IP-Adresse (Event-Entitaet).

        Der allererste Abruf (``self._last_external_ip`` noch ``None``, z. B.
        nach jedem Neustart von Home Assistant) loest bewusst nichts aus -
        die alte Adresse ist dann schlicht nicht bekannt, das ist keine
        "Aenderung". Bleibt die Abfrage der externen IP in einem Zyklus
        ohne Ergebnis, bleibt der zuletzt bekannte Wert stehen.
        """
        new_ip = (connection or {}).get("external_ip")
        if not new_ip:
            return
        old_ip = self._last_external_ip
        self._last_external_ip = new_ip
        if old_ip and new_ip != old_ip:
            for listener in list(self._external_ip_listeners):
                try:
                    listener(old_ip, new_ip)
                except Exception:  # noqa: BLE001 - ein Listener darf den Abruf nie stoppen
                    _LOGGER.exception("Fehler im 'Externe IP geaendert'-Listener")

    async def async_invalidate_address_sources(self) -> None:
        """Erzwingt beim naechsten Durchlauf eine neue IP-Typ-Abfrage."""
        self._address_source_scan = None
