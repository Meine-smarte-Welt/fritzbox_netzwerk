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

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
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
)
from .hosts import build_hosts, mac_key, summarize

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

    def _fetch(self) -> tuple[list[dict[str, Any]], bool]:
        """Blockierender Teil des Abrufs, laeuft im Executor."""
        raw_hosts = self.fritz_hosts.get_hosts_attributes()
        refreshed = False
        if self._address_sources_due():
            macs = [str(host.get("MACAddress") or "") for host in raw_hosts]
            self._fetch_address_sources(macs)
            refreshed = True
        return raw_hosts, refreshed

    def _ha_device_map(self) -> dict[str, dict[str, str]]:
        """Bildet MAC-Adressen auf Home-Assistant-Geraete ab.

        Grundlage ist die Geraeteregistrierung: jedes Geraet, das eine
        Verbindung vom Typ ``mac`` hinterlegt hat, wird ueber genau diese
        MAC-Adresse zugeordnet. Es wird nichts geraten - Geraete ohne
        MAC-Verbindung bleiben in der Karte einfach ohne HA-Namen.
        """
        registry = dr.async_get(self.hass)
        mapping: dict[str, dict[str, str]] = {}
        for device in registry.devices.values():
            if device.disabled_by is not None:
                continue
            name = device.name_by_user or device.name or ""
            for connection_type, connection_value in device.connections:
                if connection_type != dr.CONNECTION_NETWORK_MAC:
                    continue
                key = mac_key(connection_value)
                if not key or key in mapping:
                    continue
                mapping[key] = {
                    "name": name,
                    "device_id": device.id,
                    "area": device.area_id or "",
                }
        return mapping

    async def _async_update_data(self) -> dict[str, Any]:
        """Holt die Geraeteliste und reichert sie an."""
        try:
            raw_hosts, refreshed = await self.hass.async_add_executor_job(self._fetch)
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

        hosts = build_hosts(
            raw_hosts,
            self._address_sources if self.track_address_source else None,
            self._ha_device_map(),
        )

        return {
            "hosts": hosts,
            "summary": summarize(hosts),
            "last_scan": dt_util.utcnow().isoformat(),
            "address_source_scan": (
                self._address_source_scan.isoformat()
                if self._address_source_scan
                else None
            ),
            "track_address_source": self.track_address_source,
        }

    async def async_invalidate_address_sources(self) -> None:
        """Erzwingt beim naechsten Durchlauf eine neue IP-Typ-Abfrage."""
        self._address_source_scan = None
