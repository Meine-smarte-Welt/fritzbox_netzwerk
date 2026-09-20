"""Datenabruf fuer fritzbox_netzwerk."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Final

from fritzconnection import FritzConnection
from fritzconnection.core.exceptions import (
    FritzAuthorizationError,
    FritzConnectionException,
    FritzSecurityError,
    FritzServiceError,
)
from fritzconnection.lib.fritzhosts import FritzHosts
from fritzconnection.lib.fritzstatus import FritzStatus
from requests.exceptions import RequestException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_call_later, async_track_point_in_utc_time
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ADDRESS_SOURCE_INTERVAL,
    CONF_SCAN_INTERVAL,
    CONF_TRACK_ADDRESS_SOURCE,
    CONF_USE_TLS,
    DEFAULT_ADDRESS_SOURCE_INTERVAL,
    DEFAULT_PAIRING_MINUTES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TRACK_ADDRESS_SOURCE,
    DEFAULT_USE_TLS,
    DOMAIN,
    CONF_PAIRING_MINUTES,
    LAST_SEEN_STORAGE_VERSION,
    PAIRING_STORAGE_VERSION,
)
from .hosts import (
    MAC_FILTER_INFO_KEY,
    as_bool,
    build_hosts,
    is_mac_filter_band,
    mac_key,
    set_config_arguments,
    summarize,
    to_kbytes_per_s,
    to_mbit_per_s,
)

_LOGGER = logging.getLogger(__name__)

# Aktionen, mit denen die Internetverbindung neu aufgebaut wird - in dieser
# Reihenfolge probiert. Zuerst die TR-064-Dienste: sie laufen mit der
# Anmeldung der Integration (derselben, die auch den Neustart erlaubt).
# Der bis 1.5.2b0 allein genutzte UPnP-IGD-Dienst ``WANIPConn1`` (das ist
# ``FritzConnection.reconnect()``) wird von manchen FRITZ!Boxen mit Fehler
# 606 (nicht autorisiert) abgelehnt - obwohl das Konto voll berechtigt ist und
# der Neustart ueber TR-064 funktioniert. Vermutlich haengt der IGD-Zugriff an
# den UPnP-Einstellungen der Box statt an den Rechten des Kontos. IGD bleibt
# deshalb nur als letzter Rueckfallweg.
RECONNECT_ACTIONS: Final = (
    ("WANIPConnection1", "ForceTermination"),
    ("WANPPPConnection1", "ForceTermination"),
    ("WANIPConn1", "ForceTermination"),
    ("WANPPPConn1", "ForceTermination"),
)

# Zeitlimit fuer die Verbindung zu einem Repeater (Sekunden).
REPEATER_TIMEOUT: Final = 15

# Bis zum naechsten Versuch, den MAC-Filter nach dem Pairing wieder
# einzuschalten, falls die FRITZ!Box gerade nicht antwortet (Sekunden).
PAIRING_RETRY_SECONDS: Final = 60

# Dienste, die den MAC-Filter tragen: Hauptband(er), nicht das Gast-WLAN.
MAC_FILTER_SERVICES: Final = (1, 2)


class MacFilterUnsupported(FritzConnectionException):
    """Die FRITZ!Box bietet den MAC-Filter ueber TR-064 nicht an."""


class MacFilterNotApplied(FritzConnectionException):
    """Die FRITZ!Box hat die Aenderung angenommen, aber nicht uebernommen."""


class FritzboxNetzwerkCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Haelt die Geraeteliste der FRITZ!Box aktuell.

    Die eigentliche Hostliste kommt mit EINEM SOAP-Aufruf
    (``X_AVM-DE_GetHostListPath``). Die Angabe DHCP/statisch steht dort
    nicht drin - sie ist nur ueber ``GetSpecificHostEntry`` je Geraet zu
    bekommen. Diese teure Abfrage laeuft deshalb in einem eigenen,
    deutlich langsameren Takt und ihr Ergebnis wird zwischengespeichert.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        fritz_hosts: FritzHosts,
    ) -> None:
        """Initialisiert den Coordinator."""
        self.entry = entry
        self.fritz_hosts = fritz_hosts
        self._address_sources: dict[str, dict[str, Any]] = {}
        self._address_source_scan: datetime | None = None
        self._address_source_failed = False

        # Verbindungsdaten (Down/Up). FritzStatus teilt sich die Verbindung
        # mit FritzHosts. Fehlt der WAN-Dienst (z. B. FRITZ!Box im reinen
        # Access-Point-Betrieb), wird nach dem ersten Fehlschlag nicht mehr
        # abgefragt, um das Protokoll nicht vollzuschreiben.
        self._fritz_status: FritzStatus | None = None
        self._connection_supported = True

        # WLAN-Baender fuer die Steuerung: gemerkt wird, welche Dienste die
        # Box bereitstellt (1=2,4 GHz, 2=5 GHz, 3=Gast bei Dualband).
        self._wlan_supported: dict[int, bool] = {1: True, 2: True, 3: True}

        # "Zuletzt gesehen" pflegt die Integration selbst (die FRITZ!Box
        # liefert es nicht) und speichert es dauerhaft, damit die Angabe
        # einen Neustart uebersteht.
        self._last_seen: dict[str, str] = {}
        self._last_seen_store: Store[dict[str, str]] = Store(
            hass, LAST_SEEN_STORAGE_VERSION, f"{DOMAIN}.last_seen.{entry.entry_id}"
        )

        # Pairing (MAC-Filter zeitweise aus): Der Zeitpunkt, zu dem der Filter
        # wieder eingeschaltet wird, wird dauerhaft gespeichert. Startet Home
        # Assistant waehrenddessen neu, holt ``async_restore_pairing`` das nach -
        # der Filter bleibt so nicht versehentlich dauerhaft offen.
        self._pairing_until: datetime | None = None
        self._pairing_cancel: CALLBACK_TYPE | None = None
        self._pairing_store: Store[dict[str, str]] = Store(
            hass, PAIRING_STORAGE_VERSION, f"{DOMAIN}.pairing.{entry.entry_id}"
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )

    # -- Optionen ---------------------------------------------------------

    @property
    def track_address_source(self) -> bool:
        """Ob DHCP/statisch mit erfasst werden soll."""
        return self.entry.options.get(
            CONF_TRACK_ADDRESS_SOURCE, DEFAULT_TRACK_ADDRESS_SOURCE
        )

    @property
    def address_source_interval(self) -> timedelta:
        """Abstand zwischen zwei IP-Typ-Abfragen."""
        return timedelta(
            minutes=self.entry.options.get(
                CONF_ADDRESS_SOURCE_INTERVAL, DEFAULT_ADDRESS_SOURCE_INTERVAL
            )
        )

    # -- Abruf ------------------------------------------------------------

    def _address_sources_due(self) -> bool:
        """Prueft, ob die langsame IP-Typ-Abfrage jetzt faellig ist."""
        if not self.track_address_source:
            return False
        if self._address_source_scan is None:
            return True
        return dt_util.utcnow() - self._address_source_scan >= self.address_source_interval

    def _fetch_address_sources(self, macs: list[str]) -> None:
        """Holt DHCP/statisch je Geraet (ein SOAP-Aufruf pro MAC-Adresse)."""
        sources: dict[str, dict[str, Any]] = {}
        for mac in macs:
            if not mac:
                continue
            try:
                entry = self.fritz_hosts.get_specific_host_entry(mac)
            except FritzConnectionException as err:
                # Einzelne Geraete koennen der FRITZ!Box unbekannt sein
                # (z. B. Mesh-Clients hinter einem Repeater). Das ist kein
                # Grund, die gesamte Aktualisierung scheitern zu lassen.
                _LOGGER.debug("IP-Typ fuer %s nicht abrufbar: %s", mac, err)
                continue
            sources[mac_key(mac)] = {
                "address_source": entry.get("NewAddressSource"),
                "lease_time_remaining": entry.get("NewLeaseTimeRemaining"),
            }
        self._address_sources = sources

    def _fetch(
        self,
    ) -> tuple[list[dict[str, Any]], bool, dict[str, Any] | None, dict[str, bool]]:
        """Blockierender Teil des Abrufs, laeuft im Executor."""
        raw_hosts = self.fritz_hosts.get_hosts_attributes()
        refreshed = False
        if self._address_sources_due():
            macs = [str(host.get("MACAddress") or "") for host in raw_hosts]
            self._fetch_address_sources(macs)
            refreshed = True
        connection = self._fetch_connection()
        wlan = self._fetch_wlan() if self._controls_enabled else {}
        return raw_hosts, refreshed, connection, wlan

    @property
    def _controls_enabled(self) -> bool:
        """Ob die FRITZ!Box-Steuerung (WLAN/Reconnect/Neustart) aktiv ist."""
        from .const import CONF_ENABLE_CONTROLS, DEFAULT_ENABLE_CONTROLS

        return self.entry.options.get(CONF_ENABLE_CONTROLS, DEFAULT_ENABLE_CONTROLS)

    @property
    def controls_enabled(self) -> bool:
        """Oeffentlicher Zugriff auf den Steuerungs-Status (fuer den Sensor)."""
        return self._controls_enabled

    def call_action(self, service: str, action: str, **kwargs: Any) -> dict[str, Any]:
        """Fuehrt einen TR-064-Aufruf aus (blockierend, im Executor nutzen)."""
        return self.fritz_hosts.fc.call_action(service, action, **kwargs)

    def reconnect_internet(self) -> None:
        """Baut die Internetverbindung neu auf (neue oeffentliche IP).

        Blockierend, im Executor nutzen. Probiert die Aktionen aus
        ``RECONNECT_ACTIONS`` der Reihe nach. Fehlt ein Dienst auf dieser
        FRITZ!Box, geht es mit dem naechsten weiter; lehnt die Box eine
        Aktion ab (z. B. Fehler 606), ebenso. Erst wenn keine Aktion
        durchgeht, wird der Fehler des ERSTEN echten Versuchs weitergereicht -
        das ist der aussagekraeftigste.
        """
        first_error: FritzConnectionException | None = None
        for service, action in RECONNECT_ACTIONS:
            try:
                self.call_action(service, action)
            except FritzServiceError:
                _LOGGER.debug("Dienst %s gibt es auf dieser FRITZ!Box nicht", service)
                continue
            except FritzAuthorizationError:
                # Anmeldung an sich abgelehnt - weitere Versuche bringen nichts.
                raise
            except FritzConnectionException as err:
                _LOGGER.debug("%s.%s abgelehnt: %s", service, action, err)
                if first_error is None:
                    first_error = err
                continue
            _LOGGER.debug("Neuverbindung ueber %s.%s ausgeloest", service, action)
            return
        if first_error is not None:
            raise first_error
        raise FritzServiceError(
            "Kein WAN-Verbindungsdienst gefunden (weder TR-064 noch UPnP-IGD)"
        )

    def reboot_repeater(self, address: str) -> None:
        """Startet einen Repeater neu (blockierend, im Executor nutzen).

        Ein Repeater im Mesh wird ueber sein EIGENES TR-064 angesprochen -
        die Hauptbox kann fremde Geraete nicht neu starten. Verwendet werden
        dieselben Zugangsdaten wie fuer die Hauptbox. Im Mesh uebernehmen
        Repeater in der Regel die Anmeldedaten der FRITZ!Box; ist das nicht
        der Fall oder ist TR-064 am Repeater aus, lehnt er die Anmeldung ab
        und der Aufrufer bekommt eine entsprechende Fehlermeldung.
        """
        data = self.entry.data
        connection = FritzConnection(
            address=address,
            user=data[CONF_USERNAME],
            password=data[CONF_PASSWORD],
            use_tls=data.get(CONF_USE_TLS, DEFAULT_USE_TLS),
            timeout=REPEATER_TIMEOUT,
        )
        connection.call_action("DeviceConfig1", "Reboot")

    # -- MAC-Filter und Pairing -------------------------------------------

    @property
    def pairing_until(self) -> datetime | None:
        """Zeitpunkt (UTC), zu dem der Filter wieder eingeschaltet wird, sonst None."""
        return self._pairing_until

    @property
    def pairing_minutes(self) -> int:
        """Eingestellte Dauer eines Pairings (Optionen)."""
        return int(
            self.entry.options.get(CONF_PAIRING_MINUTES, DEFAULT_PAIRING_MINUTES)
        )

    def _mac_filter_bands(self) -> list[tuple[int, dict[str, Any]]]:
        """Liest ``GetInfo`` der Baender, die den MAC-Filter tragen (blockierend)."""
        bands: list[tuple[int, dict[str, Any]]] = []
        for index in MAC_FILTER_SERVICES:
            try:
                info = self.call_action(f"WLANConfiguration{index}", "GetInfo")
            except FritzServiceError:
                continue  # dieses Band gibt es an der Box nicht
            if is_mac_filter_band(index, info):
                bands.append((index, info))
        return bands

    def _mac_filter_state(self) -> bool | None:
        """Ist der MAC-Filter an? None, wenn die Box ihn nicht anbietet (blockierend)."""
        bands = self._mac_filter_bands()
        if not bands:
            return None
        return all(as_bool(info.get(MAC_FILTER_INFO_KEY)) for _, info in bands)

    def _set_mac_filter(self, enabled: bool) -> None:
        """Schaltet den MAC-Filter und prueft das Ergebnis (blockierend).

        Geschrieben wird ueber ``WLANConfiguration.SetConfig`` - dort muessen
        alle Einstellungen mit, deshalb werden die aktuellen Werte
        zurueckgeschrieben (siehe ``hosts.set_config_arguments``). Danach wird
        neu gelesen: nimmt die Box die Aenderung nicht an, gibt es einen
        Fehler statt einer stillen Falschmeldung.
        """
        bands = self._mac_filter_bands()
        if not bands:
            raise MacFilterUnsupported("WLANConfiguration ohne MAC-Filter")
        for index, info in bands:
            if as_bool(info.get(MAC_FILTER_INFO_KEY)) == enabled:
                continue
            service = f"WLANConfiguration{index}"
            try:
                action = self.fritz_hosts.fc.services[service].actions["SetConfig"]
            except KeyError as err:
                raise MacFilterUnsupported(f"{service} kennt SetConfig nicht") from err
            input_names = [
                name
                for name, argument in action.arguments.items()
                if argument.direction == "in"
            ]
            try:
                arguments = set_config_arguments(input_names, info, enabled)
            except ValueError as err:
                raise MacFilterUnsupported(
                    f"SetConfig verlangt unbekannte Werte: {err}"
                ) from err
            self.call_action(service, "SetConfig", **arguments)
        if self._mac_filter_state() is not enabled:
            raise MacFilterNotApplied(
                "MAC-Filter steht nach dem Schreiben nicht auf "
                f"{'an' if enabled else 'aus'}"
            )

    @staticmethod
    def _mac_filter_error(err: Exception) -> HomeAssistantError:
        """Uebersetzbare Fehlermeldung zu einem gescheiterten Zugriff."""
        if isinstance(err, MacFilterUnsupported):
            key = "mac_filter_unsupported"
        elif isinstance(err, MacFilterNotApplied):
            key = "mac_filter_not_applied"
        else:
            key = "mac_filter_failed"
        return HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key=key,
            translation_placeholders={"error": str(err)},
        )

    async def async_set_mac_filter(self, enabled: bool) -> None:
        """Schaltet den MAC-Filter dauerhaft an oder aus.

        Beendet ein laufendes Pairing: ein ausdruecklicher Wunsch geht der
        Zeitschaltung vor.
        """
        try:
            await self.hass.async_add_executor_job(self._set_mac_filter, enabled)
        except (FritzConnectionException, RequestException) as err:
            raise self._mac_filter_error(err) from err
        await self._async_clear_pairing()
        await self.async_request_refresh()

    async def async_start_pairing(self, minutes: int | None = None) -> None:
        """Schaltet den MAC-Filter fuer ``minutes`` Minuten aus.

        Danach schaltet die Integration ihn von selbst wieder ein. Waehrend
        des Fensters koennen sich neue Geraete am WLAN anmelden. Der Filter
        muss dafuer eingeschaltet sein - war er ohnehin ausgeschaltet, gaebe
        es nichts zu "oeffnen", und das automatische Wiedereinschalten wuerde
        gegen den Willen des Nutzers etwas aktivieren. Laeuft schon ein
        Pairing, wird es neu gestartet (Fenster verlaengert).
        """
        minutes = int(minutes or self.pairing_minutes)
        try:
            state = await self.hass.async_add_executor_job(self._mac_filter_state)
        except (FritzConnectionException, RequestException) as err:
            raise self._mac_filter_error(err) from err
        if state is None:
            raise self._mac_filter_error(MacFilterUnsupported("kein MAC-Filter"))
        if state is False and self._pairing_until is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="pairing_filter_off"
            )

        # Erst Frist merken und Wiedereinschalten einplanen, DANN ausschalten:
        # so gibt es nie einen offenen Filter ohne hinterlegtes Ende.
        until = dt_util.utcnow() + timedelta(minutes=minutes)
        await self._pairing_store.async_save({"until": until.isoformat()})
        self._pairing_until = until
        self._async_schedule_pairing_end(until)
        if state:
            try:
                await self.hass.async_add_executor_job(self._set_mac_filter, False)
            except (FritzConnectionException, RequestException) as err:
                await self._async_clear_pairing()
                # Ist nur ein Teil der Baender umgestellt worden, den Filter
                # wieder ganz einschalten - nach bestem Wissen, ohne den
                # eigentlichen Fehler zu ueberdecken.
                try:
                    await self.hass.async_add_executor_job(self._set_mac_filter, True)
                except (FritzConnectionException, RequestException) as undo_err:
                    _LOGGER.warning(
                        "MAC-Filter konnte nach dem gescheiterten Pairing-Start "
                        "nicht sicher wieder eingeschaltet werden: %s",
                        undo_err,
                    )
                raise self._mac_filter_error(err) from err
        _LOGGER.info("Pairing gestartet: MAC-Filter aus bis %s", until.isoformat())
        self.async_update_listeners()
        await self.async_request_refresh()

    @callback
    def _async_schedule_pairing_end(self, until: datetime) -> None:
        """Plant das Wiedereinschalten (ersetzt einen vorhandenen Termin)."""
        self._async_cancel_pairing_timer()
        self._pairing_cancel = async_track_point_in_utc_time(
            self.hass, self._async_end_pairing, until
        )

    @callback
    def _async_cancel_pairing_timer(self) -> None:
        """Stoppt den geplanten Termin (aendert weder Filter noch Speicher)."""
        if self._pairing_cancel is not None:
            self._pairing_cancel()
            self._pairing_cancel = None

    async def _async_clear_pairing(self) -> None:
        """Vergisst ein laufendes Pairing samt Termin und gespeicherter Frist."""
        self._async_cancel_pairing_timer()
        if self._pairing_until is not None:
            self._pairing_until = None
            self.async_update_listeners()
        await self._pairing_store.async_remove()

    async def _async_end_pairing(self, _now: datetime | None = None) -> None:
        """Schaltet den MAC-Filter nach Ablauf des Pairings wieder ein.

        Antwortet die FRITZ!Box nicht, bleibt die Frist bestehen und es wird
        nach ``PAIRING_RETRY_SECONDS`` erneut versucht - der Filter soll nicht
        offen bleiben, nur weil die Box gerade beschaeftigt war.
        """
        self._pairing_cancel = None
        try:
            await self.hass.async_add_executor_job(self._set_mac_filter, True)
        except (FritzConnectionException, RequestException) as err:
            _LOGGER.warning(
                "MAC-Filter konnte nach dem Pairing nicht wieder eingeschaltet "
                "werden (%s) - neuer Versuch in %s s",
                err,
                PAIRING_RETRY_SECONDS,
            )
            self._pairing_cancel = async_call_later(
                self.hass, PAIRING_RETRY_SECONDS, self._async_end_pairing
            )
            return
        _LOGGER.info("Pairing beendet: MAC-Filter wieder eingeschaltet")
        await self._async_clear_pairing()
        await self.async_request_refresh()

    async def async_restore_pairing(self) -> None:
        """Nimmt ein vor dem Neustart laufendes Pairing wieder auf.

        Ist die Frist abgelaufen (Home Assistant war laenger aus), wird der
        Filter sofort wieder eingeschaltet, sonst der Termin neu geplant.
        """
        stored = await self._pairing_store.async_load()
        raw = stored.get("until") if isinstance(stored, dict) else None
        try:
            until = dt_util.parse_datetime(raw) if isinstance(raw, str) else None
        except ValueError:
            until = None
        if until is None:
            if stored:
                await self._pairing_store.async_remove()
            return
        until = dt_util.as_utc(until)
        self._pairing_until = until
        if until <= dt_util.utcnow():
            _LOGGER.info("Pairing-Frist war abgelaufen - schalte MAC-Filter wieder ein")
            await self._async_end_pairing()
        else:
            self._async_schedule_pairing_end(until)

    @callback
    def async_cancel_pairing_timer(self) -> None:
        """Beim Entladen: Termin stoppen (die gespeicherte Frist bleibt bestehen)."""
        self._async_cancel_pairing_timer()

    def _fetch_wlan(self) -> dict[str, bool]:
        """Liest den An/Aus-Zustand der vorhandenen WLAN-Baender.

        Nicht vorhandene Baender (z. B. kein 5-GHz- oder Gast-WLAN) werden
        nach dem ersten Fehlschlag nicht mehr abgefragt.
        """
        state: dict[str, bool] = {}
        mac_filter: list[bool] = []
        for index in (1, 2, 3):
            if not self._wlan_supported.get(index):
                continue
            try:
                info = self.fritz_hosts.fc.call_action(
                    f"WLANConfiguration{index}", "GetInfo"
                )
            except FritzServiceError:
                self._wlan_supported[index] = False
                continue
            except FritzConnectionException as err:
                _LOGGER.debug("WLAN %s momentan nicht abrufbar: %s", index, err)
                continue
            state[f"wlan{index}"] = bool(info.get("NewEnable"))
            if is_mac_filter_band(index, info):
                mac_filter.append(as_bool(info.get(MAC_FILTER_INFO_KEY)))
        # Filter gilt nur als "an", wenn er auf allen Hauptbaendern an ist.
        if mac_filter:
            state["mac_filter"] = all(mac_filter)
        return state

    def _fetch_connection(self) -> dict[str, Any] | None:
        """Liest die aktuellen Down-/Upload-Raten und die Leitungs-Sync-Raten.

        Aktuelle Rate: Bytes/s (WANCommonIFC/GetAddonInfos), umgerechnet in
        kByte/s. Sync-Rate: Bit/s, umgerechnet in Mbit/s. Ohne WAN-Dienst
        wird die Abfrage dauerhaft ausgesetzt.
        """
        if not self._connection_supported:
            return None
        try:
            if self._fritz_status is None:
                self._fritz_status = FritzStatus(fc=self.fritz_hosts.fc)
            up_bytes, down_bytes = self._fritz_status.transmission_rate
            up_max_bits, down_max_bits = self._fritz_status.max_bit_rate
        except FritzServiceError:
            # Dieser FRITZ!Box fehlt der WAN-Dienst (z. B. Access-Point-Modus).
            self._connection_supported = False
            _LOGGER.info(
                "Verbindungsdaten (Down/Up) werden von dieser FRITZ!Box nicht "
                "bereitgestellt und daher nicht mehr abgefragt."
            )
            return None
        except FritzConnectionException as err:
            _LOGGER.debug("Verbindungsdaten momentan nicht abrufbar: %s", err)
            return None
        return {
            "down_rate": to_kbytes_per_s(down_bytes),
            "up_rate": to_kbytes_per_s(up_bytes),
            "down_max": to_mbit_per_s(down_max_bits),
            "up_max": to_mbit_per_s(up_max_bits),
        }

    def _ha_device_map(self) -> dict[str, dict[str, str]]:
        """Bildet MAC-Adressen auf Home-Assistant-Geraete ab.

        Grundlage ist die Geraeteregistrierung. Zugeordnet wird ueber die
        MAC-Adresse - primaer aus Verbindungen vom Typ ``mac``. Zusaetzlich
        werden MAC-artige Werte aus anderen Verbindungstypen und aus den
        Identifiern beruecksichtigt, weil manche Integrationen die MAC dort
        ablegen. Erkannt wird nur, was eindeutig wie eine 12-stellige
        MAC-Adresse aussieht; es wird nichts geraten.

        Auch deaktivierte Geraete werden beruecksichtigt: sie tragen
        weiterhin Name und ID und sollen in der Karte erscheinen.

        Grenze: Findet sich zu einem Geraet ueberhaupt keine MAC in der
        Registry (z. B. weil eine Integration die MAC nicht eintraegt -
        bei manchen Matter-Geraeten der Fall), kann es nicht zugeordnet
        werden. Das liegt an der jeweiligen Quell-Integration, nicht hier.
        """
        registry = dr.async_get(self.hass)
        mapping: dict[str, dict[str, str]] = {}

        def _add(raw_value: str, device: dr.DeviceEntry) -> None:
            key = mac_key(raw_value)
            # Nur echte 12-stellige MACs; die Null-MAC (00:00:...) taugt
            # laut IEEE nicht als Kennung und wird verworfen.
            if len(key) != 12 or key == "000000000000":
                return
            if key in mapping:
                return
            mapping[key] = {
                "name": device.name_by_user or device.name or "",
                "device_id": device.id,
                "area": device.area_id or "",
            }

        def _string_parts(item):
            """Liefert alle String-Elemente eines Tupels/einer Liste.

            Verbindungen und Identifier sind laut Spezifikation 2-Tupel, doch
            nicht jede Integration haelt sich daran: manche legen z. B. Identifier
            als 3-Tupel an. Festes Entpacken (``a, b = item``) wuerde dann
            abstuerzen. Deshalb wird hier ohne Annahme ueber die Laenge
            gearbeitet - jedes String-Element kommt als MAC-Kandidat in Frage,
            und ``_add`` verwirft alles, was keine echte MAC ist.
            """
            if isinstance(item, (tuple, list)):
                for element in item:
                    if isinstance(element, str):
                        yield element
            elif isinstance(item, str):
                yield item

        # Geraete dieser Integration (die Repeater) kommen zuletzt an die
        # Reihe: hat dieselbe MAC-Adresse auch ein Geraet einer anderen
        # Integration, gewinnt dieses wie bisher. So aendert das Anlegen der
        # Repeater-Geraete nichts an der bisherigen Zuordnung.
        own_entry_id = self.entry.entry_id

        def _is_own(device: dr.DeviceEntry) -> bool:
            # Neuere Home-Assistant-Staende fuehren ein Geraet nur noch unter
            # EINEM Eintrag (``config_entry_id``); ``config_entries`` ist dort
            # nur noch eine Kompatibilitaetshilfe. Aeltere kennen nur Letzteres.
            entry_id = getattr(device, "config_entry_id", None)
            if entry_id is not None:
                return entry_id == own_entry_id
            return own_entry_id in device.config_entries

        devices = sorted(self._iter_devices(registry), key=_is_own)
        for device in devices:
            # 1) Verbindungen vom Typ "mac" haben Vorrang. Nur bei einem
            #    sauberen 2-Tupel wird der Typ geprueft.
            for connection in device.connections:
                if (
                    isinstance(connection, (tuple, list))
                    and len(connection) == 2
                    and connection[0] == dr.CONNECTION_NETWORK_MAC
                ):
                    _add(connection[1], device)
            # 2) Alle MAC-artigen Werte aus Verbindungen und Identifiern -
            #    tolerant gegenueber abweichenden Tupellaengen.
            for connection in device.connections:
                for value in _string_parts(connection):
                    _add(value, device)
            for identifier in device.identifiers:
                for value in _string_parts(identifier):
                    _add(value, device)
        return mapping

    @staticmethod
    def _iter_devices(registry: dr.DeviceRegistry):
        """Iteriert die Geraete-Eintraege der Registry versionsuebergreifend.

        Seit Home Assistant 2026.9 liefert ``for x in registry.devices`` direkt
        die ``DeviceEntry``-Objekte; auf aelteren Versionen liefert dieselbe
        Iteration die Schluessel (Geraete-IDs als Strings). ``.values()`` waere
        auf neuen Versionen wiederum als veraltet markiert. Daher wird hier
        iteriert und ein String-Schluessel ueber die unterstuetzte Methode
        ``async_get`` in seinen Eintrag aufgeloest - das funktioniert auf allen
        Versionen ohne Absturz und ohne Deprecation-Warnung.
        """
        for item in registry.devices:
            device = item if not isinstance(item, str) else registry.async_get(item)
            if device is not None:
                yield device

    async def _async_update_data(self) -> dict[str, Any]:
        """Holt die Geraeteliste und reichert sie an."""
        try:
            raw_hosts, refreshed, connection, wlan = (
                await self.hass.async_add_executor_job(self._fetch)
            )
        except (FritzSecurityError, FritzAuthorizationError) as err:
            raise ConfigEntryAuthFailed(
                "Das FRITZ!Box-Konto hat keine ausreichenden Rechte. Benoetigt wird "
                "die Berechtigung 'FRITZ!Box Einstellungen'."
            ) from err
        except FritzServiceError as err:
            raise UpdateFailed(
                "Der Dienst 'Hosts' ist auf dieser FRITZ!Box nicht verfuegbar. "
                "Ist 'Zugriff fuer Anwendungen zulassen' aktiviert?"
            ) from err
        except FritzConnectionException as err:
            raise UpdateFailed(f"Abruf der Geraeteliste fehlgeschlagen: {err}") from err

        if refreshed:
            self._address_source_scan = dt_util.utcnow()

        self._update_last_seen(raw_hosts)

        hosts = build_hosts(
            raw_hosts,
            self._address_sources if self.track_address_source else None,
            self._ha_device_map(),
            self._last_seen,
        )

        return {
            "hosts": hosts,
            "summary": summarize(hosts),
            "connection": connection,
            "wlan": wlan,
            "last_scan": dt_util.utcnow().isoformat(),
            "address_source_scan": (
                self._address_source_scan.isoformat()
                if self._address_source_scan
                else None
            ),
            "track_address_source": self.track_address_source,
        }

    # -- "Zuletzt gesehen" ------------------------------------------------

    async def async_load_last_seen(self) -> None:
        """Laedt die gespeicherten 'zuletzt gesehen'-Zeitstempel beim Start."""
        stored = await self._last_seen_store.async_load()
        if isinstance(stored, dict):
            self._last_seen = {
                str(key): str(value) for key, value in stored.items() if value
            }

    def _update_last_seen(self, raw_hosts: list[dict[str, Any]]) -> None:
        """Schreibt fuer jedes aktuell aktive Geraet den Zeitpunkt mit.

        Nur aktive Geraete werden aktualisiert; inaktive behalten ihren
        letzten bekannten Wert. Geaendert wird nur bei tatsaechlicher
        Aenderung, danach wird verzoegert gespeichert (die Store-Helfer
        buendeln haeufige Schreibvorgaenge selbst).
        """
        now = dt_util.utcnow().isoformat()
        changed = False
        for raw in raw_hosts or []:
            if not raw.get("Active"):
                continue
            key = mac_key(raw.get("MACAddress"))
            if not key:
                continue
            self._last_seen[key] = now
            changed = True
        if changed:
            self._last_seen_store.async_delay_save(lambda: dict(self._last_seen), 5)

    async def async_invalidate_address_sources(self) -> None:
        """Erzwingt beim naechsten Durchlauf eine neue IP-Typ-Abfrage."""
        self._address_source_scan = None
