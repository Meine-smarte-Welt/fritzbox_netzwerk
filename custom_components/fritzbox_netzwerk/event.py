"""Event-Entitaeten der Integration fritzbox_netzwerk.

Zwei Ereignisse, beide ohne zusaetzlichen TR-064-Aufruf:

- "Neues Geraet" (``new_device``): loest aus, sobald ein Geraet erstmals in
  der Hostliste der FRITZ!Box auftaucht. Grundlage ist der ohnehin
  gefuehrte "zuletzt gesehen"-Speicher (siehe ``coordinator._update_last_seen``),
  es wird nichts zusaetzlich abgefragt. Beim allerersten Abruf nach der
  Einrichtung wird bewusst nichts gemeldet - sonst waere das komplette
  vorhandene Heimnetz "neu" (siehe ``coordinator.async_load_last_seen``).
- "Externe IP geaendert" (``changed``): loest aus, wenn sich die oeffentliche
  IPv4-Adresse gegenueber dem letzten Abruf unterscheidet. Der erste Abruf
  nach jedem Neustart von Home Assistant loest nichts aus, weil die
  vorherige Adresse dann nicht bekannt ist (kein gespeicherter Zustand).

Beide Listener werden beim Coordinator angemeldet (siehe dort) und direkt
beim naechsten Abruf synchron aufgerufen - keine eigene Abfrage, keine
Abhaengigkeit vom Polling-Zyklus der Event-Entitaet (Event-Entitaeten
pollen grundsaetzlich nicht).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.event import EventEntity
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, VERSION
from .coordinator import FritzboxNetzwerkCoordinator

if TYPE_CHECKING:
    from . import FritzboxNetzwerkConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FritzboxNetzwerkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Legt die Event-Entitaeten an und meldet sie beim Coordinator an."""
    coordinator = entry.runtime_data
    new_device = FritzboxNetzwerkNewDeviceEvent(coordinator, entry)
    external_ip = FritzboxNetzwerkExternalIpChangedEvent(coordinator, entry)
    async_add_entities([new_device, external_ip])

    entry.async_on_unload(
        coordinator.async_add_new_device_listener(new_device.handle_new_device)
    )
    entry.async_on_unload(
        coordinator.async_add_external_ip_listener(external_ip.handle_ip_change)
    )


class FritzboxNetzwerkEventBase(
    CoordinatorEntity[FritzboxNetzwerkCoordinator], EventEntity
):
    """Gemeinsame Basis der Event-Entitaeten dieser Integration."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: FritzboxNetzwerkCoordinator, entry) -> None:
        """Initialisiert die Event-Entitaet."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=MANUFACTURER,
            name=entry.title,
            configuration_url=f"http://{entry.data[CONF_HOST]}",
            sw_version=VERSION,
        )


class FritzboxNetzwerkNewDeviceEvent(FritzboxNetzwerkEventBase):
    """Meldet, wenn ein bisher unbekanntes Geraet im Heimnetz auftaucht."""

    _attr_translation_key = "neues_geraet"
    _attr_icon = "mdi:devices"
    _attr_event_types = ["new_device"]

    def __init__(self, coordinator: FritzboxNetzwerkCoordinator, entry) -> None:
        """Initialisiert die Event-Entitaet."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_new_device"

    def handle_new_device(self, host: dict[str, Any]) -> None:
        """Vom Coordinator aufgerufen, wenn ein Geraet erstmals erscheint."""
        self._trigger_event(
            "new_device",
            {
                "mac": host.get("mac"),
                "name": host.get("name"),
                "ip": host.get("ip"),
                "vendor": host.get("vendor"),
                "mac_random": host.get("mac_random"),
                "connection": host.get("connection"),
            },
        )
        self.async_write_ha_state()


class FritzboxNetzwerkExternalIpChangedEvent(FritzboxNetzwerkEventBase):
    """Meldet, wenn sich die oeffentliche IPv4-Adresse der FRITZ!Box aendert."""

    _attr_translation_key = "externe_ip_geaendert"
    _attr_icon = "mdi:ip-network"
    _attr_event_types = ["changed"]

    def __init__(self, coordinator: FritzboxNetzwerkCoordinator, entry) -> None:
        """Initialisiert die Event-Entitaet."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_external_ip_changed"

    def handle_ip_change(self, old_ip: str, new_ip: str) -> None:
        """Vom Coordinator aufgerufen, wenn sich die externe IP aendert."""
        self._trigger_event("changed", {"old_ip": old_ip, "new_ip": new_ip})
        self.async_write_ha_state()
