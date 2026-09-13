"""Sensoren der Integration fritzbox_netzwerk."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import CONF_HOST, UnitOfDataRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ACTIVE,
    ATTR_ADDRESS_SOURCE_SCAN,
    ATTR_ADDRESS_SOURCE_STATE,
    ATTR_BLOCKED,
    ATTR_GUESTS,
    ATTR_HOSTS,
    ATTR_INACTIVE,
    ATTR_LAST_SCAN,
    ATTR_STATIC,
    ATTR_TOTAL,
    ATTR_UPDATES,
    DOMAIN,
    MANUFACTURER,
    VERSION,
)
from .coordinator import FritzboxNetzwerkCoordinator

if TYPE_CHECKING:
    from . import FritzboxNetzwerkConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FritzboxNetzwerkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Legt die Sensoren an."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            FritzboxNetzwerkGeraeteSensor(coordinator, entry),
            FritzboxNetzwerkKennzahlSensor(coordinator, entry, "updates", "updates"),
            FritzboxNetzwerkKennzahlSensor(coordinator, entry, "blocked", "gesperrt"),
            # Down/Up: aktuelle Rate (kByte/s) und Leitungs-Sync-Rate (Mbit/s).
            FritzboxNetzwerkRateSensor(
                coordinator, entry, "down_rate", "download",
                UnitOfDataRate.KILOBYTES_PER_SECOND, "mdi:download",
            ),
            FritzboxNetzwerkRateSensor(
                coordinator, entry, "up_rate", "upload",
                UnitOfDataRate.KILOBYTES_PER_SECOND, "mdi:upload",
            ),
            FritzboxNetzwerkRateSensor(
                coordinator, entry, "down_max", "download_max",
                UnitOfDataRate.MEGABITS_PER_SECOND, "mdi:download-network",
            ),
            FritzboxNetzwerkRateSensor(
                coordinator, entry, "up_max", "upload_max",
                UnitOfDataRate.MEGABITS_PER_SECOND, "mdi:upload-network",
            ),
        ]
    )


class FritzboxNetzwerkBase(CoordinatorEntity[FritzboxNetzwerkCoordinator], SensorEntity):
    """Gemeinsame Basis aller Sensoren dieser Integration."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: FritzboxNetzwerkCoordinator, entry) -> None:
        """Initialisiert den Sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=MANUFACTURER,
            name=entry.title,
            configuration_url=f"http://{entry.data[CONF_HOST]}",
            sw_version=VERSION,
        )

    @property
    def _summary(self) -> dict[str, int]:
        """Kennzahlen der letzten Aktualisierung."""
        return (self.coordinator.data or {}).get("summary", {})


class FritzboxNetzwerkGeraeteSensor(FritzboxNetzwerkBase):
    """Sammelsensor: Zustand ist die Anzahl aktiver Geraete.

    Die vollstaendige Geraeteliste haengt als Attribut ``hosts`` daran -
    genau das liest die Dashboard-Karte aus.
    """

    _attr_translation_key = "geraete"
    _attr_icon = "mdi:lan"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "Geräte"
    # Ohne diese Zeile schriebe der Recorder die komplette Geraeteliste bei
    # jeder Zustandsaenderung in die Datenbank - bei 60 Geraeten sind das
    # schnell 15-20 kB pro Eintrag.
    _unrecorded_attributes = frozenset({ATTR_HOSTS})

    def __init__(self, coordinator, entry) -> None:
        """Initialisiert den Sammelsensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_geraete"

    @property
    def native_value(self) -> int | None:
        """Anzahl der aktuell verbundenen Geraete."""
        return self._summary.get("active")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Geraeteliste und Kennzahlen."""
        data = self.coordinator.data or {}
        summary = self._summary
        return {
            ATTR_HOSTS: data.get("hosts", []),
            ATTR_TOTAL: summary.get("total", 0),
            ATTR_ACTIVE: summary.get("active", 0),
            ATTR_INACTIVE: summary.get("inactive", 0),
            ATTR_GUESTS: summary.get("guests", 0),
            ATTR_BLOCKED: summary.get("blocked", 0),
            ATTR_UPDATES: summary.get("updates", 0),
            ATTR_STATIC: summary.get("static", 0),
            ATTR_LAST_SCAN: data.get("last_scan"),
            ATTR_ADDRESS_SOURCE_SCAN: data.get("address_source_scan"),
            ATTR_ADDRESS_SOURCE_STATE: data.get("track_address_source", False),
        }


class FritzboxNetzwerkKennzahlSensor(FritzboxNetzwerkBase):
    """Kleiner Zaehler-Sensor fuer Automatisierungen."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    _ICONS = {
        "updates": "mdi:package-down",
        "blocked": "mdi:web-off",
    }

    def __init__(self, coordinator, entry, key: str, slug: str) -> None:
        """Initialisiert den Zaehler."""
        super().__init__(coordinator, entry)
        self._key = key
        self._attr_translation_key = slug
        self._attr_unique_id = f"{entry.entry_id}_{slug}"
        self._attr_icon = self._ICONS.get(key, "mdi:counter")
        self._attr_native_unit_of_measurement = "Geräte"

    @property
    def native_value(self) -> int | None:
        """Aktueller Zaehlerstand."""
        return self._summary.get(self._key)


class FritzboxNetzwerkRateSensor(FritzboxNetzwerkBase):
    """Down-/Upload-Rate der FRITZ!Box-Internetverbindung.

    Liest den jeweiligen Wert aus dem ``connection``-Teil der
    Coordinator-Daten. Ist keine Verbindung ermittelbar (z. B. FRITZ!Box im
    Access-Point-Betrieb), bleibt der Zustand ``None`` und der Sensor damit
    "unbekannt".
    """

    _attr_device_class = SensorDeviceClass.DATA_RATE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator, entry, key: str, slug: str, unit, icon: str) -> None:
        """Initialisiert den Rate-Sensor."""
        super().__init__(coordinator, entry)
        self._key = key
        self._attr_translation_key = slug
        self._attr_unique_id = f"{entry.entry_id}_{slug}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon

    @property
    def native_value(self) -> float | None:
        """Aktueller Wert oder None, wenn keine Verbindungsdaten vorliegen."""
        connection = (self.coordinator.data or {}).get("connection")
        if not connection:
            return None
        return connection.get(self._key)
