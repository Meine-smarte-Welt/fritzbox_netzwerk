"""Aktions-Buttons der Integration fritzbox_netzwerk.

Erzeugt - wenn in den Optionen aktiviert - Buttons zum Neu-Verbinden der
Internetverbindung (neue IP) und zum Neustart der FRITZ!Box, einen Button
zum Starten des Pairings (MAC-Filter zeitweise aus) sowie je AVM-Repeater
einen Neustart-Button (am Repeater-Geraet).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fritzconnection.core.exceptions import (
    FritzAuthorizationError,
    FritzConnectionException,
    FritzSecurityError,
)
from requests.exceptions import RequestException

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ENABLE_CONTROLS,
    DEFAULT_ENABLE_CONTROLS,
    DOMAIN,
    MANUFACTURER,
)
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
    """Legt die Aktions-Buttons an - nur wenn die Steuerung aktiv ist."""
    if not entry.options.get(CONF_ENABLE_CONTROLS, DEFAULT_ENABLE_CONTROLS):
        return
    coordinator = entry.runtime_data
    buttons: list[ButtonEntity] = [
        FritzboxNetzwerkReconnectButton(entry),
        FritzboxNetzwerkRebootButton(entry),
    ]
    # Pairing gibt es nur, wenn die Box den MAC-Filter ueber TR-064 meldet.
    if "mac_filter" in ((coordinator.data or {}).get("wlan") or {}):
        buttons.append(FritzboxNetzwerkPairingButton(entry))
    async_add_entities(buttons)

    if not repeaters_enabled(entry):
        return

    known: set[str] = set()

    @callback
    def _add_new() -> None:
        """Ergaenzt Neustart-Buttons fuer neu aufgetauchte Repeater."""
        new_entities: list[FritzboxNetzwerkRepeaterRebootButton] = []
        for host in repeater_hosts(coordinator.data):
            key = mac_key(host["mac"])
            if key in known:
                continue
            known.add(key)
            new_entities.append(
                FritzboxNetzwerkRepeaterRebootButton(hass, coordinator, entry, host)
            )
        if new_entities:
            async_add_entities(new_entities)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class _BaseButton(ButtonEntity):
    """Gemeinsame Basis der Aktions-Buttons."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: FritzboxNetzwerkConfigEntry) -> None:
        """Merkt sich den Eintrag und setzt die Geraetezuordnung."""
        self._entry = entry
        self._coordinator = entry.runtime_data
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "manufacturer": MANUFACTURER,
            "name": entry.title,
        }


class FritzboxNetzwerkReconnectButton(_BaseButton):
    """Trennt und erneuert die Internetverbindung (neue IP)."""

    _attr_translation_key = "reconnect"
    _attr_icon = "mdi:restart"

    def __init__(self, entry: FritzboxNetzwerkConfigEntry) -> None:
        """Initialisiert den Reconnect-Button."""
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_reconnect"

    async def async_press(self) -> None:
        """Erzwingt eine neue Interneteinwahl."""
        try:
            await self.hass.async_add_executor_job(
                self._coordinator.reconnect_internet
            )
        except (FritzConnectionException, RequestException) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=(
                    "reconnect_denied"
                    if isinstance(err, FritzSecurityError)
                    else "reconnect_failed"
                ),
                translation_placeholders={"error": str(err)},
            ) from err


class FritzboxNetzwerkPairingButton(_BaseButton):
    """Schaltet den MAC-Filter fuer einige Minuten aus ("Pairing").

    In dieser Zeit koennen sich neue Geraete am WLAN anmelden; danach
    schaltet die Integration den Filter von selbst wieder ein. Die Dauer
    steht in den Integrationseinstellungen (Standard 5 Minuten).
    """

    _attr_translation_key = "pairing"
    _attr_icon = "mdi:shield-key"

    def __init__(self, entry: FritzboxNetzwerkConfigEntry) -> None:
        """Initialisiert den Pairing-Button."""
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_pairing"

    async def async_press(self) -> None:
        """Startet das Pairing-Fenster."""
        await self._coordinator.async_start_pairing()


class FritzboxNetzwerkRebootButton(_BaseButton):
    """Startet die FRITZ!Box neu."""

    _attr_translation_key = "reboot"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_icon = "mdi:restart-alert"

    def __init__(self, entry: FritzboxNetzwerkConfigEntry) -> None:
        """Initialisiert den Neustart-Button."""
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_reboot"

    async def async_press(self) -> None:
        """Loest einen Neustart der FRITZ!Box aus."""

        def _reboot() -> None:
            self._coordinator.call_action("DeviceConfig1", "Reboot")

        try:
            await self.hass.async_add_executor_job(_reboot)
        except (FritzConnectionException, RequestException) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="reboot_failed",
                translation_placeholders={"error": str(err)},
            ) from err


class FritzboxNetzwerkRepeaterRebootButton(
    CoordinatorEntity[FritzboxNetzwerkCoordinator], ButtonEntity
):
    """Startet einen Repeater neu - ueber dessen eigenes TR-064.

    Die Hauptbox kann fremde Geraete nicht neu starten. Deshalb verbindet sich
    die Integration mit denselben Zugangsdaten direkt mit dem Repeater und
    loest dort ``DeviceConfig1.Reboot`` aus.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "reboot"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:restart-alert"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: FritzboxNetzwerkCoordinator,
        entry: FritzboxNetzwerkConfigEntry,
        host: dict[str, Any],
    ) -> None:
        """Initialisiert den Button anhand der (stabilen) MAC-Adresse."""
        super().__init__(coordinator)
        self._key = mac_key(host["mac"])
        self._attr_unique_id = f"{repeater_identifier(entry, self._key)}_reboot"
        self._attr_device_info: DeviceInfo = repeater_device_info(hass, entry, host)

    async def async_press(self) -> None:
        """Loest den Neustart des Repeaters aus."""
        host = find_repeater(self.coordinator.data, self._key)
        name = (host or {}).get("name") or self._key
        address = (host or {}).get("ip") or ""
        if not address:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="repeater_no_ip",
                translation_placeholders={"name": str(name)},
            )
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.reboot_repeater, address
            )
        except (FritzAuthorizationError, FritzSecurityError) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="repeater_denied",
                translation_placeholders={
                    "name": str(name),
                    "address": address,
                    "error": str(err),
                },
            ) from err
        except (FritzConnectionException, RequestException) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="repeater_reboot_failed",
                translation_placeholders={
                    "name": str(name),
                    "address": address,
                    "error": str(err),
                },
            ) from err
