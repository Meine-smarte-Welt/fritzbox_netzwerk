"""Device-Tracker der Integration fritzbox_netzwerk.

Erzeugt - wenn in den Optionen aktiviert - je Netzwerkgeraet einen
``device_tracker`` (zuhause/abwesend anhand des Aktiv-Status der FRITZ!Box).
Damit lassen sich Anwesenheit und Automationen pro Geraet nutzen.

Neu auftauchende Geraete werden waehrend der Laufzeit automatisch als
weitere Tracker ergaenzt.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ENABLE_DEVICE_TRACKER,
    DEFAULT_ENABLE_DEVICE_TRACKER,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import FritzboxNetzwerkCoordinator
from .hosts import mac_key, normalize_mac

if TYPE_CHECKING:
    from . import FritzboxNetzwerkConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FritzboxNetzwerkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Legt die Tracker an - nur wenn der Nutzer sie eingeschaltet hat."""
    if not entry.options.get(
        CONF_ENABLE_DEVICE_TRACKER, DEFAULT_ENABLE_DEVICE_TRACKER
    ):
        return

    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        """Ergaenzt Tracker fuer neu aufgetauchte Geraete."""
        new_entities: list[FritzboxNetzwerkTracker] = []
        for host in (coordinator.data or {}).get("hosts", []):
            key = mac_key(host.get("mac"))
            if not key or key in known:
                continue
            known.add(key)
            new_entities.append(FritzboxNetzwerkTracker(coordinator, entry, host["mac"]))
        if new_entities:
            async_add_entities(new_entities)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class FritzboxNetzwerkTracker(
    CoordinatorEntity[FritzboxNetzwerkCoordinator], ScannerEntity
):
    """Ein Anwesenheits-Tracker fuer ein einzelnes Netzwerkgeraet."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: FritzboxNetzwerkCoordinator,
        entry: FritzboxNetzwerkConfigEntry,
        mac: str,
    ) -> None:
        """Initialisiert den Tracker anhand der (stabilen) MAC-Adresse."""
        super().__init__(coordinator)
        self._entry = entry
        self._mac = normalize_mac(mac)
        self._key = mac_key(mac)
        self._attr_unique_id = f"{entry.entry_id}_track_{self._key}"

    def _host(self) -> dict[str, Any] | None:
        """Sucht den zugehoerigen Host in den aktuellen Coordinator-Daten."""
        for host in (self.coordinator.data or {}).get("hosts", []):
            if mac_key(host.get("mac")) == self._key:
                return host
        return None

    @property
    def name(self) -> str:
        """Anzeigename - bevorzugt der aktuelle Geraetename, sonst die MAC."""
        host = self._host()
        if host and host.get("name"):
            return str(host["name"])
        return self._mac

    @property
    def is_connected(self) -> bool:
        """Zuhause, wenn die FRITZ!Box das Geraet als aktiv meldet."""
        host = self._host()
        return bool(host and host.get("active"))

    @property
    def source_type(self) -> SourceType:
        """Anwesenheit wird vom Router bestimmt."""
        return SourceType.ROUTER

    @property
    def ip_address(self) -> str | None:
        """Aktuelle IP-Adresse, falls bekannt."""
        host = self._host()
        return (host.get("ip") or None) if host else None

    @property
    def mac_address(self) -> str:
        """MAC-Adresse des Geraets."""
        return self._mac

    @property
    def hostname(self) -> str | None:
        """Von der FRITZ!Box gemeldeter Hostname, falls vorhanden."""
        host = self._host()
        return (host.get("host_name") or None) if host else None

    @property
    def icon(self) -> str:
        """Symbol je nach Verbindungsstatus."""
        return "mdi:lan-connect" if self.is_connected else "mdi:lan-disconnect"

    @property
    def device_info(self) -> dict[str, Any]:
        """Ordnet den Tracker dem FRITZ!Box-Geraet der Integration zu."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "manufacturer": MANUFACTURER,
            "name": self._entry.title,
        }
