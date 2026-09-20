"""WLAN-Schalter der Integration fritzbox_netzwerk.

Erzeugt - wenn in den Optionen aktiviert - je vorhandenem WLAN-Band einen
Schalter (2,4 GHz, 5 GHz, Gast-WLAN). Der Zustand kommt aus den
Coordinator-Daten, das Schalten laeuft ueber TR-064.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fritzconnection.core.exceptions import FritzConnectionException

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ENABLE_CONTROLS,
    DEFAULT_ENABLE_CONTROLS,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import FritzboxNetzwerkCoordinator

if TYPE_CHECKING:
    from . import FritzboxNetzwerkConfigEntry

# Best-effort-Zuordnung der WLAN-Dienste zu Baendern (uebliche Dualband-Box).
WLAN_BANDS = {
    1: ("wlan_24", "mdi:wifi"),
    2: ("wlan_5", "mdi:wifi"),
    3: ("wlan_guest", "mdi:wifi-lock"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FritzboxNetzwerkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Legt die WLAN-Schalter an - nur wenn die Steuerung eingeschaltet ist."""
    if not entry.options.get(CONF_ENABLE_CONTROLS, DEFAULT_ENABLE_CONTROLS):
        return

    coordinator = entry.runtime_data
    wlan = (coordinator.data or {}).get("wlan") or {}
    entities = [
        FritzboxNetzwerkWlanSwitch(coordinator, entry, index)
        for index in (1, 2, 3)
        if f"wlan{index}" in wlan
    ]
    async_add_entities(entities)


class FritzboxNetzwerkWlanSwitch(
    CoordinatorEntity[FritzboxNetzwerkCoordinator], SwitchEntity
):
    """Schaltet ein WLAN-Band der FRITZ!Box ein oder aus."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: FritzboxNetzwerkCoordinator,
        entry: FritzboxNetzwerkConfigEntry,
        index: int,
    ) -> None:
        """Initialisiert den Schalter fuer ein WLAN-Band."""
        super().__init__(coordinator)
        self._entry = entry
        self._index = index
        slug, icon = WLAN_BANDS[index]
        self._attr_translation_key = slug
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{slug}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "manufacturer": MANUFACTURER,
            "name": entry.title,
        }

    @property
    def is_on(self) -> bool | None:
        """Aktueller An/Aus-Zustand des Bandes."""
        wlan = (self.coordinator.data or {}).get("wlan") or {}
        return wlan.get(f"wlan{self._index}")

    async def _async_set(self, enable: bool) -> None:
        def _set() -> None:
            self.coordinator.call_action(
                f"WLANConfiguration{self._index}", "SetEnable", NewEnable=enable
            )

        try:
            await self.hass.async_add_executor_job(_set)
        except FritzConnectionException as err:
            raise HomeAssistantError(
                f"WLAN-Band {self._index} konnte nicht geschaltet werden: {err}"
            ) from err
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Schaltet das Band ein."""
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Schaltet das Band aus."""
        await self._async_set(False)
