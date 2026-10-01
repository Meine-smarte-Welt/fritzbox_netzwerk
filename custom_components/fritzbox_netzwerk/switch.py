"""WLAN-Schalter der Integration fritzbox_netzwerk.

Erzeugt - wenn in den Optionen aktiviert - je vorhandenem WLAN-Band einen
Schalter (2,4 GHz, 5 GHz, Gast-WLAN) sowie einen Schalter fuer den
WLAN-MAC-Filter ("Zugang auf bekannte Geraete beschraenken"). Der Zustand
kommt aus den Coordinator-Daten, das Schalten laeuft ueber TR-064.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fritzconnection.core.exceptions import FritzConnectionException

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
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
from .hosts import mac_key, normalize_mac

if TYPE_CHECKING:
    from . import FritzboxNetzwerkConfigEntry

_LOGGER = logging.getLogger(__name__)

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
    entities: list[Any] = [
        FritzboxNetzwerkWlanSwitch(coordinator, entry, index)
        for index in (1, 2, 3)
        if f"wlan{index}" in wlan
    ]
    # Der MAC-Filter erscheint nur, wenn die Box ihn ueber TR-064 meldet.
    if "mac_filter" in wlan:
        entities.append(FritzboxNetzwerkMacFilterSwitch(coordinator, entry))
    async_add_entities(entities)

    # Auto-WoL je Geraet (Idee 12): eigene, standardmaessig deaktivierte
    # Entitaeten, die unabhaengig vom gemeinsamen Koordinator-Zyklus gepollt
    # werden (siehe Docstring von FritzboxNetzwerkAutoWolSwitch). Neu
    # auftauchende Geraete werden waehrend der Laufzeit automatisch ergaenzt,
    # genau wie beim Device-Tracker.
    known: set[str] = set()

    @callback
    def _add_wol_switches() -> None:
        """Ergaenzt Auto-WoL-Schalter fuer neu aufgetauchte Geraete."""
        new_entities: list[FritzboxNetzwerkAutoWolSwitch] = []
        for host in (coordinator.data or {}).get("hosts", []):
            key = mac_key(host.get("mac"))
            if not key or key in known:
                continue
            known.add(key)
            new_entities.append(
                FritzboxNetzwerkAutoWolSwitch(coordinator, entry, host["mac"])
            )
        if new_entities:
            async_add_entities(new_entities)

    _add_wol_switches()
    entry.async_on_unload(coordinator.async_add_listener(_add_wol_switches))


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


class FritzboxNetzwerkAutoWolSwitch(SwitchEntity):
    """Schaltet "Automatisches Aufwecken" (Wake-on-LAN) fuer ein Geraet.

    Dieser Schalter ist bewusst KEINE ``CoordinatorEntity``: Home Assistants
    ``CoordinatorEntity`` setzt ``should_poll`` fest auf ``False``, weil ihr
    Zustand normalerweise beim gemeinsamen Koordinator-Abruf mitkommt. Der
    Auto-WoL-Status haengt dagegen an einem eigenen TR-064-Aufruf je Geraet
    (``X_AVM-DE_GetAutoWakeOnLANByMACAddress`` - belegt durch den Quelltext
    von ``fritzconnection.lib.fritzhosts.FritzHosts``, Version 1.15.1).
    Wuerde das bei jedem Koordinator-Zyklus fuer alle Geraete mit abgefragt,
    waechst die Zahl der SOAP-Aufrufe linear mit der Geraetezahl. Darum
    pollt dieser Schalter unabhaengig ueber ein eigenes ``async_update`` und
    ist standardmaessig deaktiviert (``entity_registry_enabled_default``) -
    wer ihn braucht, schaltet ihn gezielt je Geraet ein.

    Annahme (an echter Hardware noch nicht geprueft): Der TR-064-Aufruf
    duerfte nur fuer der FRITZ!Box bereits bekannte Geraete einen gueltigen
    Status liefern; bei unbekannten oder sehr neuen Geraeten wird ein
    Fehler erwartet und als "Status unbekannt" (``is_on is None``)
    behandelt, nicht als Ausfall des Schalters selbst.
    """

    _attr_has_entity_name = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:power-sleep"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: FritzboxNetzwerkCoordinator,
        entry: FritzboxNetzwerkConfigEntry,
        mac: str,
    ) -> None:
        """Initialisiert den Schalter anhand der (stabilen) MAC-Adresse."""
        self.coordinator = coordinator
        self._entry = entry
        self._mac = normalize_mac(mac)
        self._key = mac_key(mac)
        self._attr_unique_id = f"{entry.entry_id}_auto_wol_{self._key}"
        self._attr_is_on: bool | None = None

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
        base = (host.get("name") if host else "") or self._mac
        return f"{base} Automatisches Aufwecken"

    @property
    def available(self) -> bool:
        """Nur verfuegbar, solange die FRITZ!Box das Geraet noch kennt."""
        return self._host() is not None

    @property
    def is_on(self) -> bool | None:
        """Zuletzt abgefragter Auto-WoL-Status (None = (noch) unbekannt)."""
        return self._attr_is_on

    async def async_update(self) -> None:
        """Fragt den Auto-WoL-Status unabhaengig vom Koordinator ab."""

        def _get() -> bool:
            return self.coordinator.fritz_hosts.get_wakeonlan_status(self._mac)

        try:
            self._attr_is_on = await self.hass.async_add_executor_job(_get)
        except FritzConnectionException as err:
            _LOGGER.debug(
                "Auto-WoL-Status fuer %s nicht abrufbar: %s", self._mac, err
            )
            self._attr_is_on = None

    async def _async_set(self, enable: bool) -> None:
        def _set() -> None:
            self.coordinator.fritz_hosts.set_wakeonlan_status(self._mac, enable)

        try:
            await self.hass.async_add_executor_job(_set)
        except FritzConnectionException as err:
            raise HomeAssistantError(
                f"Automatisches Aufwecken konnte nicht geschaltet werden: {err}"
            ) from err
        self._attr_is_on = enable
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Schaltet automatisches Aufwecken fuer dieses Geraet ein."""
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Schaltet automatisches Aufwecken fuer dieses Geraet aus."""
        await self._async_set(False)

    @property
    def device_info(self) -> dict[str, Any]:
        """Ordnet den Schalter dem FRITZ!Box-Geraet der Integration zu."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "manufacturer": MANUFACTURER,
            "name": self._entry.title,
        }
