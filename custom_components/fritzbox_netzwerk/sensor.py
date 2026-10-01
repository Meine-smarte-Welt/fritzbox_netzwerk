"""Sensoren der Integration fritzbox_netzwerk."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, CONF_HOST, UnitOfDataRate, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

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
    CONF_IP_RANGES,
    DEFAULT_IP_RANGES,
    DOMAIN,
    MANUFACTURER,
    VERSION,
)
from .coordinator import FritzboxNetzwerkCoordinator
from .hosts import (
    BAND_2_4,
    BAND_5,
    BAND_6,
    count_band,
    count_ip_range,
    dhcp_pool_usage,
    mac_key,
    mesh_summary,
    normalize_mac,
    parse_ip_ranges,
    slowest_mesh_link,
)
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
            # Seit 1.6.2: externe IP und Online-Zeit der Internetverbindung
            # (Standard-TR-064, derselbe Dienst wie die Down-/Upload-Raten).
            FritzboxNetzwerkExternalIpSensor(coordinator, entry),
            FritzboxNetzwerkOnlineSinceSensor(coordinator, entry),
        ]
        # Idee 7 aus feature-ideen.md: ein Zaehler je benanntem IP-Bereich aus
        # den Integrationsoptionen, z. B. "Drucker online: 2 von 3". Ohne
        # konfigurierte Bereiche entsteht kein einziger dieser Sensoren.
        + [
            FritzboxNetzwerkIpRangeSensor(coordinator, entry, ip_range)
            for ip_range in parse_ip_ranges(
                entry.options.get(CONF_IP_RANGES, DEFAULT_IP_RANGES)
            )
        ]
    )

    # Idee 21 (experimentell): CPU/RAM/Temperatur aus der Weboberflaeche - nur
    # auf ausdruecklichen Wunsch (Option), siehe webui.py.
    if coordinator.system_stats_enabled:
        async_add_entities(
            [
                FritzboxNetzwerkSystemSensor(coordinator, entry, "cpu", "cpu_auslastung", "mdi:cpu-64-bit", PERCENTAGE),
                FritzboxNetzwerkSystemSensor(coordinator, entry, "ram", "ram_auslastung", "mdi:memory", PERCENTAGE),
                FritzboxNetzwerkSystemSensor(
                    coordinator, entry, "temperature", "cpu_temperatur", "mdi:thermometer", UnitOfTemperature.CELSIUS
                ),
            ]
        )

    # Idee 7 aus feature-ideen.md: Zaehler "WLAN 2,4 GHz" / "WLAN 5 GHz" - nur
    # sinnvoll, wenn das Funkband ueberhaupt erfasst wird (siehe
    # coordinator.track_wlan_band), sonst waere jeder Zaehler immer 0.
    if coordinator.track_wlan_band:
        async_add_entities(
            [
                FritzboxNetzwerkBandSensor(coordinator, entry, BAND_2_4),
                FritzboxNetzwerkBandSensor(coordinator, entry, BAND_5),
            ]
        )
        # 6-GHz-WLAN ist (Stand 2026) noch selten; der Sensor entsteht erst,
        # sobald tatsaechlich ein Geraet in diesem Band auftaucht - wie beim
        # Mesh-Sensor unten, damit nicht jede Installation einen dauerhaft
        # leeren 6-GHz-Zaehler bekommt.
        band6_added = False

        @callback
        def _add_band6() -> None:
            nonlocal band6_added
            if band6_added:
                return
            hosts = (coordinator.data or {}).get("hosts", [])
            if not any(host.get("band") == BAND_6 for host in hosts):
                return
            band6_added = True
            async_add_entities([FritzboxNetzwerkBandSensor(coordinator, entry, BAND_6)])

        _add_band6()
        entry.async_on_unload(coordinator.async_add_listener(_add_band6))

    # Idee 8 aus feature-ideen.md: Belegung des DHCP-Bereichs. Der Bereich
    # steht erst nach dem ersten erfolgreichen ``LANHostConfigManagement1``-
    # Abruf fest (siehe coordinator._dhcp_pool_due) - deshalb wie beim
    # Mesh-Sensor erst dynamisch ergaenzen, statt mit einem dauerhaft
    # "nicht verfuegbaren" Sensor zu starten.
    pool_added = False

    @callback
    def _add_dhcp_pool() -> None:
        nonlocal pool_added
        if pool_added or coordinator.dhcp_pool is None:
            return
        pool_added = True
        async_add_entities([FritzboxNetzwerkDhcpPoolSensor(coordinator, entry)])

    _add_dhcp_pool()
    entry.async_on_unload(coordinator.async_add_listener(_add_dhcp_pool))

    # Idee 5 aus feature-ideen.md: "Schwaechstes Geraet" - entsteht erst,
    # sobald ueberhaupt ein Geraet eine bekannte Mesh-Verbindungsrate hat
    # (setzt also mindestens einen Repeater UND eine erfolgreich abgerufene
    # Mesh-Topologie voraus, siehe coordinator._fetch_mesh_topology).
    weakest_added = False

    @callback
    def _add_weakest() -> None:
        nonlocal weakest_added
        if weakest_added:
            return
        hosts = (coordinator.data or {}).get("hosts", [])
        if slowest_mesh_link(hosts) is None:
            return
        weakest_added = True
        async_add_entities([FritzboxNetzwerkWeakestLinkSensor(coordinator, entry)])

    _add_weakest()
    entry.async_on_unload(coordinator.async_add_listener(_add_weakest))

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


class FritzboxNetzwerkSystemSensor(FritzboxNetzwerkBase):
    """CPU-Auslastung, RAM-Auslastung oder Temperatur der Box (EXPERIMENTELL).

    Die Werte kommen NICHT aus TR-064, sondern aus der Weboberflaeche der Box
    (``data.lua``, Seite ``ecoStat``) - siehe ``webui.py``. Es sind Momentwerte
    aus einem Verlauf, die Zuordnung ist an keiner echten Box geprueft.
    """

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = True

    def __init__(self, coordinator, entry, key, translation_key, icon, unit) -> None:
        """Initialisiert den Sensor."""
        super().__init__(coordinator, entry)
        self._key = key
        self._attr_translation_key = translation_key
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"{entry.entry_id}_system_{key}"

    @property
    def native_value(self) -> float | None:
        """Letzter gelesener Wert oder ``None``."""
        system = (self.coordinator.data or {}).get("system")
        return (system or {}).get(self._key)


class FritzboxNetzwerkExternalIpSensor(FritzboxNetzwerkBase):
    """Aktuelle oeffentliche IPv4-Adresse der FRITZ!Box.

    Standard-TR-064 (``WANIPConn``/``GetExternalIPAddress``), derselbe Dienst,
    der schon fuer die Down-/Upload-Raten verwendet wird - kein zusaetzlicher
    SOAP-Aufruf fuer eine Box ohne diesen Dienst. Bleibt ``None`` ohne eigene
    oeffentliche IPv4 (z. B. DS-Lite) oder wenn die Box im reinen
    Access-Point-Betrieb laeuft. Fuer eine Automation bei Aenderung siehe die
    Event-Entitaet "Externe IP geaendert".
    """

    _attr_translation_key = "externe_ip"
    _attr_icon = "mdi:ip-network-outline"

    def __init__(self, coordinator, entry) -> None:
        """Initialisiert den Sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_external_ip"

    @property
    def native_value(self) -> str | None:
        """Aktuelle externe IPv4-Adresse, oder ``None``."""
        connection = (self.coordinator.data or {}).get("connection")
        return (connection or {}).get("external_ip")


class FritzboxNetzwerkOnlineSinceSensor(FritzboxNetzwerkBase):
    """Zeitpunkt, seit dem die aktuelle Internetverbindung steht.

    Berechnet aus der von der FRITZ!Box gemeldeten Verbindungs-Uptime
    (``WANIPConn``/``GetStatusInfo``, Feld ``NewUptime``) relativ zu "jetzt" -
    bewusst NICHT aus ``DeviceInfo1``/``GetInfo`` (Geraete-Uptime), das manche
    Boxen (beobachtet: FRITZ!Box 5690 Pro) mit HTTP 401 ablehnen, siehe
    ``config_flow.py``. Dadurch kann der angezeigte Zeitpunkt von Abfrage zu
    Abfrage um ein paar Sekunden schwanken - das ist kosmetisch und bewusst
    in Kauf genommen, statt eine zweite, fehleranfaellige Abfrage einzufuehren.
    """

    _attr_translation_key = "online_seit"
    _attr_icon = "mdi:clock-start"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, entry) -> None:
        """Initialisiert den Sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_online_since"

    @property
    def native_value(self):
        """Zeitpunkt des Verbindungsaufbaus, oder ``None``."""
        connection = (self.coordinator.data or {}).get("connection")
        uptime = (connection or {}).get("uptime")
        if not isinstance(uptime, int) or uptime < 0:
            return None
        return dt_util.utcnow() - timedelta(seconds=uptime)


class FritzboxNetzwerkIpRangeSensor(FritzboxNetzwerkBase):
    """Zaehler-Sensor fuer einen benannten IP-Bereich aus den Optionen.

    Idee 7 aus feature-ideen.md: Passend zum Kartenfeld ``ip_filter`` lassen
    sich in den Integrationseinstellungen benannte Bereiche anlegen (z. B.
    "Drucker=192.168.2.*"), aus denen je ein Sensor "<Name> online: 2 von 3"
    fuer Automationen entsteht. Der Zustand ist die Zahl AKTIVER Geraete im
    Bereich; die Gesamtzahl (unabhaengig vom Online-Status) steht als
    Attribut daneben.

    Der Name kommt direkt vom Nutzer (kein ``translation_key``) - ebenso wie
    bei einem per Hand benannten Geraet in Home Assistant ueblich.
    """

    _attr_icon = "mdi:lan-check"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "Geräte"

    def __init__(self, coordinator, entry, ip_range: dict[str, Any]) -> None:
        """Initialisiert den Bereichs-Sensor."""
        super().__init__(coordinator, entry)
        self._ip_range = ip_range
        self._attr_name = ip_range["name"]
        self._attr_unique_id = f"{entry.entry_id}_bereich_{slugify(ip_range['name'])}"

    @property
    def native_value(self) -> int:
        """Anzahl der aktuell aktiven Geraete in diesem Bereich."""
        hosts = (self.coordinator.data or {}).get("hosts", [])
        return count_ip_range(hosts, self._ip_range)["active"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Gesamtzahl der Geraete im Bereich (aktiv und inaktiv) sowie das Muster."""
        hosts = (self.coordinator.data or {}).get("hosts", [])
        counts = count_ip_range(hosts, self._ip_range)
        return {"gesamt": counts["total"], "muster": self._ip_range["pattern"]}


class FritzboxNetzwerkBandSensor(FritzboxNetzwerkBase):
    """Zaehler-Sensor fuer ein WLAN-Funkband (Idee 7 aus feature-ideen.md).

    Zustand ist die Zahl der aktuell aktiven Geraete in diesem Band; die
    Gesamtzahl (auch inaktive, zuletzt dort verbundene Geraete) steht als
    Attribut daneben. Setzt voraus, dass "WLAN-Band je Gerät erfassen"
    eingeschaltet ist (siehe ``async_setup_entry``) - sonst bliebe ``band``
    bei jedem Geraet leer und der Sensor zeigte dauerhaft 0.
    """

    # Die Einheit kommt - wie bei "geraete"/"updates"/"gesperrt"/"mesh" - aus
    # den Uebersetzungen (``unit_of_measurement`` in strings.json): zusaetzlich
    # ``_attr_native_unit_of_measurement`` zu setzen, bricht bei einem Sensor
    # mit ``translation_key`` mit einem Fehler ab.
    _attr_icon = "mdi:wifi"
    _attr_state_class = SensorStateClass.MEASUREMENT

    _TRANSLATION_KEYS = {BAND_2_4: "band_24", BAND_5: "band_5", BAND_6: "band_6"}

    def __init__(self, coordinator, entry, band: str) -> None:
        """Initialisiert den Band-Sensor."""
        super().__init__(coordinator, entry)
        self._band = band
        self._attr_translation_key = self._TRANSLATION_KEYS[band]
        self._attr_unique_id = f"{entry.entry_id}_{self._attr_translation_key}"

    @property
    def native_value(self) -> int:
        """Anzahl der aktuell aktiven Geraete in diesem Band."""
        hosts = (self.coordinator.data or {}).get("hosts", [])
        return count_band(hosts, self._band)["active"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Gesamtzahl der Geraete in diesem Band (aktiv und inaktiv)."""
        hosts = (self.coordinator.data or {}).get("hosts", [])
        return {"gesamt": count_band(hosts, self._band)["total"]}


class FritzboxNetzwerkDhcpPoolSensor(FritzboxNetzwerkBase):
    """Belegung des DHCP-Bereichs der FRITZ!Box (Idee 8 aus feature-ideen.md).

    Zustand ist die Zahl aktuell aktiver Geraete mit einer Adresse im
    DHCP-Bereich (siehe ``hosts.dhcp_pool_usage`` fuer die Annahme dahinter -
    TR-064 liefert keine echte Lease-Tabelle); die Attribute nennen
    Gesamtgroesse, freie Adressen und den Prozentsatz. Entsteht erst, sobald
    der Bereich einmal erfolgreich ermittelt wurde (siehe ``async_setup_entry``).
    """

    # Einheit kommt aus den Uebersetzungen, siehe Hinweis bei FritzboxNetzwerkBandSensor.
    _attr_translation_key = "dhcp_pool"
    _attr_icon = "mdi:ip-network"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry) -> None:
        """Initialisiert den DHCP-Auslastungssensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_dhcp_pool"

    def _usage(self) -> dict[str, int] | None:
        hosts = (self.coordinator.data or {}).get("hosts", [])
        return dhcp_pool_usage(hosts, self.coordinator.dhcp_pool)

    @property
    def available(self) -> bool:
        """Nicht verfuegbar, wenn der DHCP-Bereich (nicht mehr) bekannt ist."""
        return super().available and self._usage() is not None

    @property
    def native_value(self) -> int | None:
        """Zahl der aktuell belegten Adressen im Pool."""
        usage = self._usage()
        return usage["used"] if usage else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Gesamtgroesse, freie Adressen und Auslastung in Prozent."""
        usage = self._usage()
        if not usage:
            return {}
        total = usage["total"]
        percent = round(usage["used"] * 100 / total, 1) if total else 0
        return {
            "gesamt": total,
            "frei": usage["free"],
            "auslastung_prozent": percent,
        }


class FritzboxNetzwerkWeakestLinkSensor(FritzboxNetzwerkBase):
    """Das Geraet mit der aktuell langsamsten Mesh-Verbindung (Idee 5).

    Zustand ist der Geraetename, die Rate (Mbit/s) und die MAC-Adresse
    stehen als Attribut daneben. Bewusst ueber die Verbindungsrate statt
    einer Signalstaerke in dBm - siehe Begruendung in
    ``hosts.slowest_mesh_link``, dort auch der Hinweis, dass die genaue
    Mesh-JSON-Struktur nicht an echter Hardware verifiziert ist.
    """

    _attr_translation_key = "schwaechstes_geraet"
    _attr_icon = "mdi:wifi-strength-1"

    def __init__(self, coordinator, entry) -> None:
        """Initialisiert den Sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_weakest_link"

    def _weakest(self) -> dict[str, Any] | None:
        hosts = (self.coordinator.data or {}).get("hosts", [])
        return slowest_mesh_link(hosts)

    @property
    def available(self) -> bool:
        """Nicht verfuegbar, solange keine Mesh-Verbindungsraten bekannt sind."""
        return super().available and self._weakest() is not None

    @property
    def native_value(self) -> str | None:
        """Name des Geraets mit der langsamsten aktuellen Verbindung."""
        weakest = self._weakest()
        return weakest["name"] if weakest else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """MAC-Adresse, Verbindungsrate und Mesh-Nachbar des Geraets."""
        weakest = self._weakest()
        if not weakest:
            return {}
        return {
            "mac": weakest.get("mac"),
            "verbindungsrate_mbit": weakest.get("link_mbit"),
            "verbunden_ueber": weakest.get("connected_via"),
        }
