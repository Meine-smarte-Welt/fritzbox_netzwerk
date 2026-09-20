"""Verbunden-Status der Repeater als eigene Geraete.

Fuer jeden AVM-Repeater in der Hostliste der FRITZ!Box entsteht ein eigenes
Home-Assistant-Geraet (haengt an der FRITZ!Box) mit einem
``binary_sensor`` "Verbunden". Damit lassen sich Ausfaelle eines Repeaters in
Automationen auswerten. Neu auftauchende Repeater werden waehrend der
Laufzeit automatisch ergaenzt. Abschaltbar in den Integrationseinstellungen.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import FritzboxNetzwerkCoordinator
from .hosts import mac_key
from .repeater import (
    find_repeater,
    repeater_device_info,
    repeater_hosts,
    repeater_identifier,
    repeaters_enabled,
)

if TYPE_CHECKING:
    from . import FritzboxNetzwerkConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FritzboxNetzwerkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Legt je Repeater einen Verbunden-Sensor an (wenn eingeschaltet)."""
    if not repeaters_enabled(entry):
        return

    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        """Ergaenzt Sensoren fuer neu aufgetauchte Repeater."""
        new_entities: list[FritzboxNetzwerkRepeaterOnline] = []
        for host in repeater_hosts(coordinator.data):
            key = mac_key(host["mac"])
            if key in known:
                continue
            known.add(key)
            new_entities.append(
                FritzboxNetzwerkRepeaterOnline(hass, coordinator, entry, host)
            )
        if new_entities:
            async_add_entities(new_entities)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class FritzboxNetzwerkRepeaterOnline(
    CoordinatorEntity[FritzboxNetzwerkCoordinator], BinarySensorEntity
):
    """Zeigt, ob ein Repeater gerade mit der FRITZ!Box verbunden ist."""

    _attr_has_entity_name = True
    _attr_translation_key = "repeater_online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: FritzboxNetzwerkCoordinator,
        entry: FritzboxNetzwerkConfigEntry,
        host: dict[str, Any],
    ) -> None:
        """Initialisiert den Sensor anhand der (stabilen) MAC-Adresse."""
        super().__init__(coordinator)
        self._key = mac_key(host["mac"])
        self._attr_unique_id = f"{repeater_identifier(entry, self._key)}_online"
        self._attr_device_info: DeviceInfo = repeater_device_info(hass, entry, host)

    def _host(self) -> dict[str, Any] | None:
        """Der zugehoerige Repeater in den aktuellen Coordinator-Daten."""
        return find_repeater(self.coordinator.data, self._key)

    @property
    def available(self) -> bool:
        """Nicht verfuegbar, wenn der Repeater nicht (mehr) in der Liste steht."""
        return super().available and self._host() is not None

    @property
    def is_on(self) -> bool | None:
        """Verbunden, wenn die FRITZ!Box den Repeater als aktiv meldet."""
        host = self._host()
        return bool(host.get("active")) if host else None
