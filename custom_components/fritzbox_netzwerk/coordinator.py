"""Datenabruf fuer fritzbox_netzwerk."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from fritzconnection.core.exceptions import (
    FritzAuthorizationError,
    FritzConnectionException,
    FritzSecurityError,
    FritzServiceError,
)
from fritzconnection.lib.fritzhosts import FritzHosts
from fritzconnection.lib.fritzstatus import FritzStatus

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ADDRESS_SOURCE_INTERVAL,
    CONF_SCAN_INTERVAL,
    CONF_TRACK_ADDRESS_SOURCE,
    DEFAULT_ADDRESS_SOURCE_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TRACK_ADDRESS_SOURCE,
    DOMAIN,
    LAST_SEEN_STORAGE_VERSION,
)
from .hosts import build_hosts, mac_key, summarize, to_kbytes_per_s, to_mbit_per_s

_LOGGER = logging.getLogger(__name__)


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
    ) -> None:
        """Initialisiert den Coordinator."""
        self.entry = entry
        self.fritz_hosts = fritz_hosts
        self._address_sources: dict[str, dict[str, Any]] = {}
        self._address_source_scan: datetime | None = None
        self._address_source_failed = False

        # Verbindungsdaten (Down/Up). FritzStatus teilt sich die Verbindung
        # mit FritzHosts. Fehlt der WAN-Dienst (z. B. FRITZ!Box im reinen
        # Access-Point-Betrieb), wird nach dem ersten Fehlschlag nicht mehr
        # abgefragt, um das Protokoll nicht vollzuschreiben.
        self._fritz_status: FritzStatus | None = None
        self._connection_supported = True

        # "Zuletzt gesehen" pflegt die Integration selbst (die FRITZ!Box
        # liefert es nicht) und speichert es dauerhaft, damit die Angabe
        # einen Neustart uebersteht.
        self._last_seen: dict[str, str] = {}
        self._last_seen_store: Store[dict[str, str]] = Store(
            hass, LAST_SEEN_STORAGE_VERSION, f"{DOMAIN}.last_seen.{entry.entry_id}"
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
            sources[mac_key(mac)] = {
                "address_source": entry.get("NewAddressSource"),
                "lease_time_remaining": entry.get("NewLeaseTimeRemaining"),
            }
        self._address_sources = sources

    def _fetch(self) -> tuple[list[dict[str, Any]], bool, dict[str, Any] | None]:
        """Blockierender Teil des Abrufs, laeuft im Executor."""
        raw_hosts = self.fritz_hosts.get_hosts_attributes()
        refreshed = False
        if self._address_sources_due():
            macs = [str(host.get("MACAddress") or "") for host in raw_hosts]
            self._fetch_address_sources(macs)
            refreshed = True
        connection = self._fetch_connection()
        return raw_hosts, refreshed, connection

    def _fetch_connection(self) -> dict[str, Any] | None:
        """Liest die aktuellen Down-/Upload-Raten und die Leitungs-Sync-Raten.

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
        }

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

        for device in registry.devices:
            # 1) Verbindungen vom Typ "mac" haben Vorrang.
            for connection_type, connection_value in device.connections:
                if connection_type == dr.CONNECTION_NETWORK_MAC:
                    _add(connection_value, device)
            # 2) MAC-artige Werte aus anderen Verbindungstypen.
            for _connection_type, connection_value in device.connections:
                _add(connection_value, device)
            # 3) MAC-artige Identifier (z. B. ("integration", "aabbccddeeff")).
            for _domain, identifier in device.identifiers:
                _add(identifier, device)
        return mapping

    async def _async_update_data(self) -> dict[str, Any]:
        """Holt die Geraeteliste und reichert sie an."""
        try:
            raw_hosts, refreshed, connection = await self.hass.async_add_executor_job(
                self._fetch
            )
        except (FritzSecurityError, FritzAuthorizationError) as err:
            raise ConfigEntryAuthFailed(
                "Das FRITZ!Box-Konto hat keine ausreichenden Rechte. Benoetigt wird "
                "die Berechtigung 'FRITZ!Box Einstellungen'."
            ) from err
        except FritzServiceError as err:
            raise UpdateFailed(
                "Der Dienst 'Hosts' ist auf dieser FRITZ!Box nicht verfuegbar. "
                "Ist 'Zugriff fuer Anwendungen zulassen' aktiviert?"
            ) from err
        except FritzConnectionException as err:
            raise UpdateFailed(f"Abruf der Geraeteliste fehlgeschlagen: {err}") from err

        if refreshed:
            self._address_source_scan = dt_util.utcnow()

        self._update_last_seen(raw_hosts)

        hosts = build_hosts(
            raw_hosts,
            self._address_sources if self.track_address_source else None,
            self._ha_device_map(),
            self._last_seen,
        )

        return {
            "hosts": hosts,
            "summary": summarize(hosts),
            "connection": connection,
            "last_scan": dt_util.utcnow().isoformat(),
            "address_source_scan": (
                self._address_source_scan.isoformat()
                if self._address_source_scan
                else None
            ),
            "track_address_source": self.track_address_source,
        }

    # -- "Zuletzt gesehen" ------------------------------------------------

    async def async_load_last_seen(self) -> None:
        """Laedt die gespeicherten 'zuletzt gesehen'-Zeitstempel beim Start."""
        stored = await self._last_seen_store.async_load()
        if isinstance(stored, dict):
            self._last_seen = {
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

    async def async_invalidate_address_sources(self) -> None:
        """Erzwingt beim naechsten Durchlauf eine neue IP-Typ-Abfrage."""
        self._address_source_scan = None
