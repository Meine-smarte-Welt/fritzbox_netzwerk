"""Aktions-Buttons der Integration fritzbox_netzwerk.

Erzeugt - wenn in den Optionen aktiviert - Buttons zum Neu-Verbinden der
Internetverbindung (neue IP) und zum Neustart der FRITZ!Box.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fritzconnection.core.exceptions import (
    FritzConnectionException,
    FritzServiceError,
)

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ENABLE_CONTROLS,
    DEFAULT_ENABLE_CONTROLS,
    DOMAIN,
    MANUFACTURER,
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
    async_add_entities(
        [
            FritzboxNetzwerkReconnectButton(entry),
            FritzboxNetzwerkRebootButton(entry),
        ]
    )


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

        def _reconnect() -> None:
            # fritzconnection kennt reconnect() (WANIPConn1:ForceTermination).
            # Bei reinen PPPoE-Anschluessen fehlt dieser Dienst - dann ueber
            # die PPP-Verbindung neu einwaehlen.
            fc = self._coordinator.fritz_hosts.fc
            try:
                fc.reconnect()
                return
            except FritzServiceError:
                fc.call_action("WANPPPConn1", "ForceTermination")

        try:
            await self.hass.async_add_executor_job(_reconnect)
        except FritzConnectionException as err:
            raise HomeAssistantError(
                f"Neuverbindung fehlgeschlagen: {err}"
            ) from err


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
        except FritzConnectionException as err:
            raise HomeAssistantError(f"Neustart fehlgeschlagen: {err}") from err
