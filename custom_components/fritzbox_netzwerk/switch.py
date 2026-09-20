"""WLAN-Schalter der Integration fritzbox_netzwerk.

Erzeugt - wenn in den Optionen aktiviert - je vorhandenem WLAN-Band einen
Schalter (2,4 GHz, 5 GHz, Gast-WLAN) sowie einen Schalter fuer den
WLAN-MAC-Filter ("Zugang auf bekannte Geraete beschraenken"). Der Zustand
kommt aus den Coordinator-Daten, das Schalten laeuft ueber TR-064.
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
    # Der MAC-Filter erscheint nur, wenn die Box ihn ueber TR-064 meldet.
    if "mac_filter" in wlan:
        entities.append(FritzboxNetzwerkMacFilterSwitch(coordinator, entry))
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


class FritzboxNetzwerkMacFilterSwitch(
    CoordinatorEntity[FritzboxNetzwerkCoordinator], SwitchEntity
):
    """WLAN-MAC-Filter: "Zugang auf bekannte WLAN-Geraete beschraenken".

    An = nur bereits bekannte Geraete duerfen ins WLAN. Aus = jedes Geraet
    mit dem richtigen Kennwort darf sich anmelden. Fuer das zeitweise
    Freigeben neuer Geraete gibt es zusaetzlich den Button "Pairing starten"
    bzw. den Dienst ``fritzbox_netzwerk.start_pairing``.

    Wer den Schalter ausdruecklich betaetigt, beendet damit auch ein
    laufendes Pairing: Einschalten schliesst das Fenster sofort, Ausschalten
    macht die Freigabe dauerhaft.
    """

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "mac_filter"

    def __init__(
        self,
        coordinator: FritzboxNetzwerkCoordinator,
        entry: FritzboxNetzwerkConfigEntry,
    ) -> None:
        """Initialisiert den Schalter."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_mac_filter"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "manufacturer": MANUFACTURER,
            "name": entry.title,
        }

    @property
    def is_on(self) -> bool | None:
        """Ob der Filter aktiv ist (auf allen Hauptbaendern)."""
        wlan = (self.coordinator.data or {}).get("wlan") or {}
        return wlan.get("mac_filter")

    @property
    def icon(self) -> str:
        """Schild zu, wenn der Filter schuetzt - sonst durchgestrichen."""
        return "mdi:shield-lock" if self.is_on else "mdi:shield-off"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Pairing-Status: laeuft eines, und wann wird der Filter wieder aktiv?"""
        until = self.coordinator.pairing_until
        return {
            "pairing_active": until is not None,
            "pairing_ends": until.isoformat() if until else None,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Schaltet den Filter ein (beendet ein laufendes Pairing)."""
        await self.coordinator.async_set_mac_filter(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Schaltet den Filter dauerhaft aus."""
        await self.coordinator.async_set_mac_filter(False)
