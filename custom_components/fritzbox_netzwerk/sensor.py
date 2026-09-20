"""Sensoren der Integration fritzbox_netzwerk."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import CONF_HOST, UnitOfDataRate
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers import entity_registry as er
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
from .hosts import mac_key, mesh_summary, normalize_mac
from .repeater import repeater_hosts, repeaters_enabled

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

    # Der Mesh-Sensor entsteht, sobald es neben der Box einen Repeater gibt.
    if not repeaters_enabled(entry):
        return
    mesh_added = False

    @callback
    def _add_mesh() -> None:
        nonlocal mesh_added
        if mesh_added or not repeater_hosts(coordinator.data):
            return
        mesh_added = True
        async_add_entities([FritzboxNetzwerkMeshSensor(coordinator, entry)])

    _add_mesh()
    entry.async_on_unload(coordinator.async_add_listener(_add_mesh))


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
    # Die Einheit ("Geräte" / "devices" / "apparaten") kommt aus den
    # Uebersetzungen (``unit_of_measurement`` in strings.json) - sie darf hier
    # NICHT als ``_attr_native_unit_of_measurement`` stehen: Home Assistant
    # bricht bei beidem gleichzeitig mit einem Fehler ab.
    # Ohne die naechste Zeile schriebe der Recorder die komplette Geraeteliste bei
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
        """Geraeteliste, Kennzahlen sowie - fuer die Karte - Verbindungsdaten
        und (falls aktiviert) die Steuerungs-Entitaeten."""
        data = self.coordinator.data or {}
        summary = self._summary
        attributes: dict[str, Any] = {
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
            # Live-Down/Up (kann None sein) - die Karte zeigt es in der
            # optionalen Steuerungsleiste an.
            "connection": data.get("connection"),
            # Steuerungs-Entitaeten (WLAN-Schalter, Reconnect, Neustart), damit
            # die Karte sie generisch bedienen kann. None, wenn die Steuerung
            # in den Integrationseinstellungen nicht aktiviert ist.
            "controls": self._controls_attribute(),
            # Mesh-Gruppe (FRITZ!Box + Repeater) fuer die Karte; None ohne Repeater.
            "mesh": self._mesh_attribute(),
            "trackers": self._trackers_attribute(),
        }
        return attributes

    def _trackers_attribute(self) -> dict[str, str] | None:
        """Ordnet MAC-Schluessel den device_tracker-Entitaeten zu.

        Ermoeglicht der Karte, im Detail-Popup direkt zum Anwesenheits-
        Tracker eines Geraets zu verlinken. None, wenn die Tracker in den
        Integrationseinstellungen nicht aktiviert sind.
        """
        from .const import CONF_ENABLE_DEVICE_TRACKER, DEFAULT_ENABLE_DEVICE_TRACKER

        if not self._entry.options.get(
            CONF_ENABLE_DEVICE_TRACKER, DEFAULT_ENABLE_DEVICE_TRACKER
        ):
            return None
        registry = er.async_get(self.hass)
        entry_id = self._entry.entry_id
        mapping: dict[str, str] = {}
        for host in (self.coordinator.data or {}).get("hosts", []):
            key = mac_key(host.get("mac"))
            if not key:
                continue
            # WICHTIG: Home Assistants ``ScannerEntity`` ueberschreibt
            # die unique_id-Eigenschaft und gibt IMMER die MAC-Adresse zurueck -
            # unser ``_attr_unique_id`` im Tracker greift dort also gar nicht.
            # Die Registry kennt den Tracker deshalb unter der MAC, nicht unter
            # "<entry_id>_track_<mac>". Bis 1.5.1 wurde nur der zweite, nie
            # vergebene Schluessel gesucht - die Zuordnung blieb dadurch immer
            # leer und die Karte zeigte keine Anwesenheits-Zeile.
            eid = registry.async_get_entity_id(
                "device_tracker", DOMAIN, normalize_mac(host.get("mac"))
            )
            if not eid:
                # Rueckfallweg, falls Home Assistant die unique_id eines Tages
                # doch aus ``_attr_unique_id`` uebernimmt.
                eid = registry.async_get_entity_id(
                    "device_tracker", DOMAIN, f"{entry_id}_track_{key}"
                )
            if eid:
                mapping[key] = eid
        return mapping

    def _mesh_attribute(self) -> dict[str, Any] | None:
        """Die Mesh-Gruppe fuer die Karte: Mitglieder, Zaehler, Neustart-Button."""
        members = (self.coordinator.data or {}).get("mesh") or []
        if len(members) < 2:
            return None
        registry = er.async_get(self.hass)
        reboot_all = None
        if self.coordinator.controls_enabled:
            reboot_all = registry.async_get_entity_id(
                "button", DOMAIN, f"{self._entry.entry_id}_reboot_mesh"
            )
        return {
            "members": members,
            **mesh_summary(members),
            "reboot_all": reboot_all,
        }

    def _controls_attribute(self) -> dict[str, Any] | None:
        """Loest die Steuerungs-Entitaeten ueber die Registry auf.

        Liefert deren entity_id (fuer generische Dienstaufrufe der Karte)
        und - fuer die WLAN-Schalter - den aktuellen An/Aus-Zustand.
        """
        if not self.coordinator.controls_enabled:
            return None
        registry = er.async_get(self.hass)
        entry_id = self._entry.entry_id

        def _eid(platform: str, suffix: str) -> str | None:
            return registry.async_get_entity_id(platform, DOMAIN, f"{entry_id}_{suffix}")

        wlan_states = (self.coordinator.data or {}).get("wlan") or {}
        wlan: list[dict[str, Any]] = []
        for index, key in ((1, "wlan_24"), (2, "wlan_5"), (3, "wlan_guest")):
            eid = _eid("switch", key)
            if not eid:
                continue
            wlan.append(
                {"key": key, "entity_id": eid, "on": wlan_states.get(f"wlan{index}")}
            )
        until = self.coordinator.pairing_until
        return {
            "wlan": wlan,
            "reconnect": _eid("button", "reconnect"),
            "reboot": _eid("button", "reboot"),
            "reboot_mesh": _eid("button", "reboot_mesh"),
            # MAC-Filter und Pairing (None, wenn die Box den Filter nicht meldet).
            "mac_filter": _eid("switch", "mac_filter"),
            "mac_filter_on": wlan_states.get("mac_filter"),
            "pairing": _eid("button", "pairing"),
            "pairing_ends": until.isoformat() if until else None,
        }


class FritzboxNetzwerkMeshSensor(FritzboxNetzwerkBase):
    """Mesh-Gruppe: wie viele FRITZ!-Geraete (Box + Repeater) sind online?

    Der Zustand ist die Zahl der erreichbaren Geraete; die Attribute nennen
    Gesamtzahl, ob das Mesh vollstaendig ist, und jedes Mitglied einzeln -
    etwa fuer eine Automation "ein Repeater ist ausgefallen".
    """

    _attr_translation_key = "mesh"
    _attr_icon = "mdi:router-network"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _unrecorded_attributes = frozenset({"members"})

    def __init__(self, coordinator, entry) -> None:
        """Initialisiert den Mesh-Sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_mesh"

    @property
    def _members(self) -> list[dict[str, Any]]:
        return (self.coordinator.data or {}).get("mesh") or []

    @property
    def native_value(self) -> int | None:
        """Anzahl erreichbarer FRITZ!-Geraete im Mesh."""
        members = self._members
        return mesh_summary(members)["online"] if members else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Gesamtzahl, Vollstaendigkeit und die einzelnen Mitglieder."""
        members = self._members
        summary = mesh_summary(members) if members else {"total": 0, "complete": False}
        return {
            "gesamt": summary["total"],
            "vollstaendig": summary["complete"],
            "members": members,
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
