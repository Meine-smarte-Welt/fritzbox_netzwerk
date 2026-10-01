"""Aufbereitung der FRITZ!Box-Hostliste.

Dieses Modul enthaelt bewusst KEINE Home-Assistant- und keine
fritzconnection-Importe. Dadurch laesst sich die gesamte Aufbereitungs-
logik ohne laufende Home-Assistant-Instanz mit ``unittest`` pruefen.

Eingabe ist die Liste, die ``FritzHosts.get_hosts_attributes()`` liefert:
je Host ein Dictionary mit den ROHEN XML-Tagnamen der FRITZ!Box als
Schluessel (``IPAddress``, ``MACAddress``, ``X_AVM-DE_Speed`` usw.).

Wichtig und in fritzconnection 1.15.1 verifiziert: nur ``Index``,
``X_AVM-DE_Port`` und ``X_AVM-DE_Speed`` kommen als ``int`` an und nur
``Active``, ``X_AVM-DE_UpdateAvailable``, ``X_AVM-DE_Guest``,
``X_AVM-DE_VPN`` und ``X_AVM-DE_Disallow`` als ``bool``. Alle uebrigen
Felder - auch klar boolesche wie ``X_AVM-DE_IsMeshable`` oder
``X_AVM-DE_Priority`` - kommen als String ``"0"``/``"1"`` an. Deshalb
werden hier durchgaengig ``as_bool()``/``as_int()`` verwendet, die beide
Faelle abdecken. Fehlende Tags fehlen im Dictionary komplett, daher
ueberall ``.get()``.
"""

from __future__ import annotations

import csv
import io
import re
import sys
from typing import Any, Final
from xml.etree import ElementTree

TRUE_STRINGS = {"1", "true", "yes", "on", "granted"}

# Verbindungsarten, wie die FRITZ!Box sie in ``InterfaceType`` meldet.
CONNECTION_LAN = "lan"
CONNECTION_WLAN = "wlan"
CONNECTION_POWERLINE = "powerline"
CONNECTION_UNKNOWN = "unbekannt"

WAN_GRANTED = "granted"
WAN_DENIED = "denied"

ADDRESS_SOURCE_STATIC = "Static"
ADDRESS_SOURCE_DHCP = "DHCP"


def as_bool(value: Any) -> bool:
    """Wandelt FRITZ!Box-Wahrheitswerte in echte ``bool`` um.

    Akzeptiert ``bool``, ``int`` und String-Varianten (``"0"``/``"1"``).
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in TRUE_STRINGS
    return False


def as_int(value: Any, default: int = 0) -> int:
    """Wandelt einen Wert in ``int`` um, ohne bei Muell zu scheitern."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def normalize_mac(mac: Any) -> str:
    """Vereinheitlicht eine MAC-Adresse auf Grossbuchstaben mit Doppelpunkten."""
    if not mac:
        return ""
    raw = "".join(ch for ch in str(mac) if ch.isalnum()).upper()
    if len(raw) != 12:
        return str(mac).strip().upper()
    return ":".join(raw[i : i + 2] for i in range(0, 12, 2))


def mac_key(mac: Any) -> str:
    """Vergleichsschluessel fuer MAC-Adressen (klein, ohne Trennzeichen)."""
    if not mac:
        return ""
    return "".join(ch for ch in str(mac) if ch.isalnum()).lower()


# --- Hersteller aus der MAC-Adresse (OUI) --------------------------------

# Praefixe, die das IEEE selbst als Verwalter fuehrt: Der eigentliche Inhaber
# steht dann in den kleineren MA-M/MA-S-Registern (seit 1.6.3 unterstuetzt,
# siehe OUI_PREFIX_LENGTHS/vendor_for unten - die Zeilen dafuer muessen aber
# zusaetzlich in data/oui.txt stehen, siehe scripts/update_oui.py). Ohne eine
# solche Zeile waere ein Treffer auf diesen Eintrag selbst keine Auskunft,
# deshalb gilt der Hersteller in dem Fall weiterhin als unbekannt.
UNRESOLVED_OWNERS: Final = frozenset({"ieee registration authority"})

# IEEE fuehrt drei Register unterschiedlicher Groesse (siehe
# https://standards.ieee.org/products-programs/regauth/):
# MA-L ("OUI", 24 Bit, 6 Hex-Zeichen) fuer grosse Hersteller, MA-M (28 Bit,
# 7 Hex-Zeichen) und MA-S (36 Bit, 9 Hex-Zeichen) fuer kleinere Hersteller
# mit weniger benoetigten Adressen - genau die Smart-Home-Hersteller, die
# bisher oft als "unbekannt" erschienen (Idee 4a aus feature-ideen.md).
# Absteigend sortiert: ein 9-stelliger MA-S-Treffer ist spezifischer als ein
# zufaellig passender 6-stelliger MA-L-Teilstring und hat deshalb Vorrang.
OUI_PREFIX_LENGTHS: Final = (9, 7, 6)

_OUI_PREFIX = re.compile(
    "|".join(rf"[0-9A-F]{{{length}}}" for length in OUI_PREFIX_LENGTHS)
)


def mac_prefix(mac: Any) -> str:
    """Die ersten drei Byte einer MAC-Adresse (6 Hex-Zeichen, gross), sonst ``""``."""
    prefix = mac_key(mac).upper()[:6]
    return prefix if _OUI_PREFIX.fullmatch(prefix) else ""


def is_random_mac(mac: Any) -> bool:
    """Ob die MAC-Adresse "lokal verwaltet" ist (Bit 0x02 im ersten Byte).

    Registrierte Hersteller-Praefixe haben dieses Bit praktisch nie gesetzt
    (nur eine Handvoll Altlasten aus den Anfangsjahren, siehe ``apply_vendors``).
    Gesetzt ist es bei zufaelligen Adressen ("Private WLAN-Adresse" bei iPhone
    und Android, Windows), aber auch bei manchen virtuellen Geraeten (Docker,
    VMs). Ein Hersteller laesst sich daraus nicht ableiten.
    """
    prefix = mac_prefix(mac)
    return bool(prefix) and bool(int(prefix[:2], 16) & 0x02)


def parse_oui(lines: Any) -> dict[str, str]:
    """Liest Zeilen der Form ``AABBCC:Herstellername`` in ein Woerterbuch.

    Leere Zeilen, Kommentare (``#``) und unbrauchbare Zeilen werden
    uebersprungen. Bei doppelten Praefixen gilt der letzte Eintrag.
    """
    table: dict[str, str] = {}
    for line in lines:
        text = str(line).strip()
        if not text or text.startswith("#"):
            continue
        prefix, sep, name = text.partition(":")
        prefix = prefix.strip().upper()
        name = " ".join(name.split())
        if not sep or not name or not _OUI_PREFIX.fullmatch(prefix):
            continue
        if name.lower() in UNRESOLVED_OWNERS:
            continue
        # Viele Praefixe teilen sich einen Namen - einmal ablegen spart Speicher.
        table[prefix] = sys.intern(name)
    return table


def load_oui(path: str) -> dict[str, str]:
    """Laedt eine OUI-Datei (blockierend, im Executor aufrufen)."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        return parse_oui(handle)


def vendor_for(mac: Any, oui: dict[str, str] | None) -> str:
    """Hersteller zu einer MAC-Adresse; leer, wenn unbekannt.

    Probiert die Praefix-Laengen aus ``OUI_PREFIX_LENGTHS`` von der
    spezifischsten (MA-S, 9 Hex-Zeichen) zur allgemeinsten (MA-L, 6
    Hex-Zeichen): ``oui.txt`` kann Zeilen in allen drei Laengen enthalten,
    ein laengerer (spezifischerer) Treffer gilt vor einem kuerzeren.
    """
    if not oui:
        return ""
    key = mac_key(mac).upper()
    for length in OUI_PREFIX_LENGTHS:
        vendor = oui.get(key[:length])
        if vendor:
            return vendor
    return ""


def apply_vendors(
    hosts: list[dict[str, Any]], oui: dict[str, str] | None
) -> list[dict[str, Any]]:
    """Ergaenzt den Hersteller anhand der MAC-Adresse.

    Steht ein Praefix in der Tabelle, ist es KEINE zufaellige Adresse - auch
    dann nicht, wenn das "lokal verwaltet"-Bit gesetzt ist: Aus der Fruehzeit
    der Registrierung gibt es einige solcher Eintraege (etwa alte 3Com-Karten).
    """
    if not oui:
        return hosts
    for host in hosts:
        vendor = vendor_for(host["mac"], oui)
        host["vendor"] = vendor
        if vendor:
            host["mac_random"] = False
    return hosts


def ip_sort_key(ip: Any) -> tuple[int, ...]:
    """Sortierschluessel, der IPv4-Adressen numerisch statt alphabetisch ordnet.

    ``192.168.178.9`` liegt damit korrekt vor ``192.168.178.10``.
    Nicht parsebare oder leere Adressen wandern ans Ende.
    """
    text = str(ip or "").strip()
    parts = text.split(".")
    if len(parts) != 4:
        return (1, 0, 0, 0, 0)
    try:
        octets = tuple(int(part) for part in parts)
    except ValueError:
        return (1, 0, 0, 0, 0)
    if any(octet < 0 or octet > 255 for octet in octets):
        return (1, 0, 0, 0, 0)
    return (0, *octets)


def connection_kind(interface_type: Any) -> str:
    """Ordnet ``InterfaceType`` einer der internen Verbindungsarten zu."""
    text = str(interface_type or "").strip().lower()
    if text.startswith("ethernet"):
        return CONNECTION_LAN
    if text.startswith("802.11"):
        return CONNECTION_WLAN
    if text.startswith("homeplug"):
        return CONNECTION_POWERLINE
    return CONNECTION_UNKNOWN


def connection_label(kind: str, port: int, guest: bool) -> str:
    """Erzeugt die Anzeigebezeichnung der Verbindung, z. B. ``"LAN 2"``."""
    if kind == CONNECTION_LAN:
        label = f"LAN {port}" if port else "LAN"
    elif kind == CONNECTION_WLAN:
        label = "WLAN"
    elif kind == CONNECTION_POWERLINE:
        label = "Powerline"
    else:
        label = "—"
    if guest and kind != CONNECTION_UNKNOWN:
        return f"{label} (Gast)"
    if guest:
        return "Gast"
    return label


def is_repeater(model: Any) -> bool:
    """Erkennt ein FRITZ!-Mesh-Geraet anhand der gemeldeten Modellbezeichnung.

    Die FRITZ!Box traegt bei eigenen Geraeten im Mesh das Modell ein, z. B.
    ``FRITZ!Repeater 1200 AX`` oder ``FRITZ!Repeater 6000`` - das wird erkannt.
    Im Mesh kann aber auch eine zweite FRITZ!Box als WLAN-Repeater mitlaufen
    (z. B. zwei FRITZ!Box 7490 oder eine FRITZ!Box 7590 als Repeater an einer
    FRITZ!Box 5690 Pro); ihr gemeldetes Modell lautet dann schlicht
    ``FRITZ!Box 7590`` statt ``FRITZ!Repeater ...`` und wurde bis 1.6.1 nicht
    erkannt - solche Geraete fehlten dadurch komplett in der Mesh-Gruppe und
    im `mesh`-Attribut (zwei Nutzerrueckmeldungen, siehe release-1.6.2.md).
    Erkannt wird deshalb zusaetzlich "fritz!box" im Modell. Die eigene Box
    taucht nach Beobachtung nicht in ihrer eigenen Geraeteliste auf, ein
    Duplikat ist daher nicht zu erwarten (Annahme, an echter Hardware nicht
    nachstellbar). Es wird weiterhin nichts aus dem Hostnamen geraten -
    nur das von der FRITZ!Box selbst gemeldete Modell entscheidet.
    """
    text = str(model or "").strip().lower()
    return "repeater" in text or "fritz!box" in text


def display_name(raw: dict[str, Any]) -> str:
    """Bester verfuegbarer Anzeigename des Geraets.

    Reihenfolge: vom Nutzer vergebener Name (FriendlyName) vor dem vom
    Geraet gemeldeten Hostnamen, zuletzt die MAC-Adresse.
    """
    for key in ("X_AVM-DE_FriendlyName", "HostName"):
        value = str(raw.get(key) or "").strip()
        if value:
            return value
    mac = normalize_mac(raw.get("MACAddress"))
    return mac or "Unbekanntes Geraet"


def normalize_host(raw: dict[str, Any]) -> dict[str, Any]:
    """Uebersetzt einen Roh-Hosteintrag in das Format der Dashboard-Karte."""
    mac = normalize_mac(raw.get("MACAddress"))
    kind = connection_kind(raw.get("InterfaceType"))
    port = as_int(raw.get("X_AVM-DE_Port"))
    guest = as_bool(raw.get("X_AVM-DE_Guest"))
    wan_access = str(raw.get("X_AVM-DE_WANAccess") or "unknown").strip().lower()
    model = str(raw.get("X_AVM-DE_Model") or "").strip()

    return {
        "index": as_int(raw.get("Index")),
        "name": display_name(raw),
        "host_name": str(raw.get("HostName") or "").strip(),
        "friendly_name": str(raw.get("X_AVM-DE_FriendlyName") or "").strip(),
        "name_writeable": as_bool(raw.get("X_AVM-DE_FriendlyNameIsWriteable")),
        "ip": str(raw.get("IPAddress") or "").strip(),
        "mac": mac,
        # Wird in ``apply_vendors()`` ergaenzt. ``mac_random`` steht dagegen
        # fest: zufaellige (private) Adressen haben keinen Hersteller.
        "vendor": "",
        "mac_random": is_random_mac(mac),
        "active": as_bool(raw.get("Active")),
        "connection": kind,
        "connection_label": connection_label(kind, port, guest),
        # Wird in ``apply_bands()`` ergaenzt: Funkband, in dem das Geraet gerade
        # verbunden ist ("2.4", "5" oder "6"), sonst "" (LAN, offline oder
        # nicht ermittelbar).
        "band": "",
        "port": port,
        "speed": as_int(raw.get("X_AVM-DE_Speed")),
        "guest": guest,
        "vpn": as_bool(raw.get("X_AVM-DE_VPN")),
        "meshable": as_bool(raw.get("X_AVM-DE_IsMeshable")),
        "priority": as_bool(raw.get("X_AVM-DE_Priority")),
        "model": model,
        # AVM-Repeater im Mesh - bekommen (optional) ein eigenes Geraet in
        # Home Assistant, siehe binary_sensor.py und button.py.
        "repeater": is_repeater(model),
        "device_class": str(raw.get("X_AVM-DE_DeviceClass") or "").strip(),
        "device_class_user": str(raw.get("X_AVM-DE_DeviceClassUser") or "").strip(),
        "update_available": as_bool(raw.get("X_AVM-DE_UpdateAvailable")),
        "update_state": str(raw.get("X_AVM-DE_UpdateSuccessful") or "unknown").strip(),
        "info_url": str(raw.get("X_AVM-DE_InfoURL") or "").strip(),
        "url": str(raw.get("X_AVM-DE_URL") or "").strip(),
        "wan_access": wan_access,
        # ``Disallow`` ist das Flag hinter "Internetzugang gesperrt".
        # ``WANAccess == denied`` wird zusaetzlich ausgewertet, weil aeltere
        # FRITZ!OS-Staende nur eines von beiden zuverlaessig fuellen.
        "blocked": as_bool(raw.get("X_AVM-DE_Disallow")) or wan_access == WAN_DENIED,
        "filter_profile": str(raw.get("X_AVM-DE_FilterProfileID") or "").strip(),
        # Wird - falls aktiviert - nachtraeglich aus GetSpecificHostEntry
        # ergaenzt, siehe ``apply_address_sources()``.
        "address_source": None,
        "static_ip": None,
        "lease_time_remaining": None,
        # Aussagekraeftige Klassifizierung der IP-Vergabe (in build_hosts
        # gesetzt): "none" (kein IP), "dynamic" (aus dem DHCP-Pool, laeuft
        # ab), "fixed" (fest/reserviert) oder None (noch unbekannt).
        "ip_class": None,
        # Wird in ``apply_ha_devices()`` ergaenzt.
        "ha_name": "",
        "ha_device_id": "",
        "ha_area": "",
        # Wird in ``apply_last_seen()`` ergaenzt: Zeitpunkt (ISO), zu dem das
        # Geraet zuletzt als aktiv gesehen wurde. Die FRITZ!Box liefert das
        # NICHT - die Integration schreibt es selbst mit.
        "last_seen": None,
        # Wird in ``apply_mesh_links()`` ergaenzt (Idee 5 aus feature-ideen.md):
        # Name des Mesh-Nachbarn (FRITZ!Box oder Repeater), ueber den dieses
        # Geraet gerade verbunden ist, und die aktuelle Verbindungsrate in
        # Mbit/s. Bleibt leer/None ohne eindeutige Mesh-Verbindung - siehe
        # dortigen Hinweis.
        "connected_via": "",
        "link_mbit": None,
        # Wird in ``apply_notes()`` ergaenzt (Idee 3 aus feature-ideen.md):
        # eigenes Etikett, freie Notiz und die manuelle Markierung
        # "reserviert" - alles nur in Home Assistant gespeichert, die
        # FRITZ!Box wird dafuer nicht veraendert.
        "label": "",
        "note": "",
        "reserved": False,
    }


def apply_address_sources(
    hosts: list[dict[str, Any]], sources: dict[str, dict[str, Any]] | None
) -> list[dict[str, Any]]:
    """Ergaenzt DHCP/statisch und Lease-Restzeit anhand des MAC-Schluessels.

    ``sources`` bildet ``mac_key`` auf ein Dictionary mit den Schluesseln
    ``address_source`` und ``lease_time_remaining`` ab. Ist fuer einen Host
    nichts hinterlegt, bleiben die Felder ``None`` - die Karte zeigt dann
    bewusst "—" statt einer geratenen Angabe.
    """
    if not sources:
        return hosts
    for host in hosts:
        entry = sources.get(mac_key(host["mac"]))
        if not entry:
            continue
        source = str(entry.get("address_source") or "").strip()
        if source:
            host["address_source"] = source
            host["static_ip"] = source.lower() == ADDRESS_SOURCE_STATIC.lower()
        lease = entry.get("lease_time_remaining")
        if lease is not None:
            host["lease_time_remaining"] = as_int(lease)
    return hosts


def dhcp_pool(info: dict[str, Any] | None) -> tuple[int, int] | None:
    """DHCP-Bereich der FRITZ!Box aus ``LANHostConfigManagement1.GetInfo``.

    Ergebnis ist ``(erste, letzte)`` Adresse als Zahl (siehe ``ipv4_number``)
    oder ``None``, wenn der DHCP-Server aus ist oder die Angaben fehlen bzw.
    unbrauchbar sind.
    """
    if not info:
        return None
    if "NewDHCPServerEnable" in info and not as_bool(info.get("NewDHCPServerEnable")):
        return None
    low = ipv4_number(info.get("NewMinAddress"))
    high = ipv4_number(info.get("NewMaxAddress"))
    if low is None or high is None or low > high:
        return None
    return low, high


def ipv4_number(ip: Any) -> int | None:
    """IPv4-Adresse als Zahl (fuer Bereichsvergleiche), sonst ``None``."""
    key = ip_sort_key(ip)
    if key[0] != 0:
        return None
    number = 0
    for octet in key[1:]:
        number = number * 256 + octet
    return number


def classify_ip(
    host: dict[str, Any], pool: tuple[int, int] | None = None
) -> str | None:
    """Ermittelt, wie die IP-Adresse eines Geraets vergeben ist.

    Grundlage ist die Angabe der FRITZ!Box (``AddressSource``):

    - ``Static``: am Geraet selbst fest eingestellt -> fest.
    - ``DHCP``: von der Box vergeben -> dynamisch. Ausnahme: Die Adresse
      liegt AUSSERHALB des DHCP-Bereichs der Box. Das geht nur mit einer
      Reservierung ("Diesem Netzwerkgeraet immer die gleiche IPv4-Adresse
      zuweisen" mit einer Adresse ausserhalb des Pools) -> fest.

    Die Lease-Restzeit entscheidet bewusst NICHT mehr: Viele FRITZ!OS-
    Versionen melden fuer alle Geraete 0 - bis 1.5.2 wurde dadurch jedes
    DHCP-Geraet als "fest" angezeigt. Eine Reservierung INNERHALB des Pools
    ist ueber TR-064 nicht erkennbar und erscheint als dynamisch.

    Rueckgabe:
    - "none"   : Geraet ohne IP-Adresse (z. B. einfacher Switch, Powerline)
    - "dynamic": von der Box per DHCP vergeben
    - "fixed"  : am Geraet fest eingestellt oder ausserhalb des Pools reserviert
    - None     : noch nicht bekannt (IP-Typ-Erfassung aus oder noch nicht gelaufen)
    """
    if not host.get("ip"):
        return "none"
    source = str(host.get("address_source") or "").strip().lower()
    if not source:
        lease = host.get("lease_time_remaining")
        return "dynamic" if isinstance(lease, int) and lease > 0 else None
    if source == ADDRESS_SOURCE_STATIC.lower():
        return "fixed"
    if pool is not None:
        number = ipv4_number(host.get("ip"))
        if number is not None and not pool[0] <= number <= pool[1]:
            return "fixed"
    return "dynamic"


def classify_ip_with_reserved(
    host: dict[str, Any], pool: tuple[int, int] | None = None
) -> str | None:
    """Wie ``classify_ip``, beruecksichtigt aber die manuelle Markierung "reserviert".

    Die Box meldet Reservierungen INNERHALB des DHCP-Bereichs ueber TR-064
    nicht (siehe ``classify_ip``). Der Nutzer kann sie selbst kennzeichnen
    (Idee 3 aus feature-ideen.md, nur in Home Assistant gespeichert); ein so
    markiertes Geraet mit Adresse zaehlt dann als "fest". Ein Geraet ohne IP
    bleibt "none".
    """
    result = classify_ip(host, pool)
    if host.get("reserved") and result in ("dynamic", None):
        return "fixed"
    return result


def apply_ha_devices(
    hosts: list[dict[str, Any]], devices: dict[str, dict[str, str]] | None
) -> list[dict[str, Any]]:
    """Ergaenzt den Home-Assistant-Geraetenamen anhand des MAC-Schluessels."""
    if not devices:
        return hosts
    for host in hosts:
        entry = devices.get(mac_key(host["mac"]))
        if not entry:
            continue
        host["ha_name"] = entry.get("name", "")
        host["ha_device_id"] = entry.get("device_id", "")
        host["ha_area"] = entry.get("area", "")
    return hosts


def apply_last_seen(
    hosts: list[dict[str, Any]], last_seen: dict[str, str] | None
) -> list[dict[str, Any]]:
    """Ergaenzt den Zeitpunkt, zu dem ein Geraet zuletzt aktiv gesehen wurde.

    ``last_seen`` bildet ``mac_key`` auf einen ISO-Zeitstempel ab. Die Werte
    pflegt der Coordinator ueber die Zeit und speichert sie dauerhaft, da die
    FRITZ!Box selbst keinen solchen Zeitstempel liefert.
    """
    if not last_seen:
        return hosts
    for host in hosts:
        stamp = last_seen.get(mac_key(host["mac"]))
        if stamp:
            host["last_seen"] = stamp
    return hosts


def apply_first_seen(
    hosts: list[dict[str, Any]], first_seen: dict[str, str] | None
) -> list[dict[str, Any]]:
    """Ergaenzt den Zeitpunkt, zu dem ein Geraet zum ersten Mal gesehen wurde.

    ``first_seen`` bildet ``mac_key`` auf einen ISO-Zeitstempel ab und wird
    vom Coordinator genau dann geschrieben, wenn ein Geraet erstmals als
    "neu" erkannt wird (``_process_new_devices``, dieselbe Grundlage wie das
    Ereignis "Neues Geraet"). Fuer alle Geraete, die schon vor 1.6.3
    bestanden (und damit schon in ``last_seen`` standen, bevor diese
    Zeiterfassung eingefuehrt wurde), fehlt bewusst ein Wert - sie wuerden
    sonst beim Update auf 1.6.3 faelschlich als "neu" erscheinen. Ein
    fehlender Wert bedeutet fuer die Karte deshalb "nicht neu", nicht
    "unbekannt".
    """
    if not first_seen:
        return hosts
    for host in hosts:
        stamp = first_seen.get(mac_key(host["mac"]))
        if stamp:
            host["first_seen"] = stamp
    return hosts


# --- WLAN-Band je Geraet -------------------------------------------------

BAND_2_4: Final = "2.4"
BAND_5: Final = "5"
BAND_6: Final = "6"


def frequency_band(value: Any) -> str:
    """Wandelt die Frequenzangabe der FRITZ!Box in ``"2.4"``, ``"5"`` oder ``"6"``.

    Laut AVM-Beschreibung meldet ``NewX_AVM-DE_FrequencyBand`` 2400, 5000
    oder 6000. Weitere Schreibweisen ("5GHz", "2,4 GHz") werden ebenfalls
    erkannt; alles andere - auch "unknown" - ergibt ``""``.
    """
    if value is None or isinstance(value, bool):
        return ""
    text = str(value).strip().lower().replace(",", ".").replace(" ", "")
    if text.startswith(("2.4", "24")):
        return BAND_2_4
    if text.startswith("5"):
        return BAND_5
    if text.startswith("6"):
        return BAND_6
    return ""


def band_from_channel(channel: Any) -> str:
    """Band anhand der Kanalnummer: 1-14 = 2,4 GHz, 32-177 = 5 GHz, sonst ``""``.

    Bei 6 GHz ueberschneiden sich die Kanalnummern mit denen der anderen
    Baender - dort entscheidet allein die Angabe des Dienstes.
    """
    number = as_int(channel, 0)
    if 1 <= number <= 14:
        return BAND_2_4
    if 32 <= number <= 177:
        return BAND_5
    return ""


def device_band(service_band: str, channel: Any) -> str:
    """Band eines WLAN-Geraets aus Dienst-Band und Kanal.

    Meldet der Dienst ausdruecklich 6 GHz, gilt das fuer alle seine Geraete.
    Sonst zeigt der Kanal des Geraets das Band verlaesslich. So wird auch das
    Gast-WLAN richtig eingeordnet, dessen Dienst kein eigenes Band melden
    muss. Fehlt der Kanal, bleibt die Angabe des Dienstes.
    """
    if service_band == BAND_6:
        return BAND_6
    return band_from_channel(channel) or service_band


def list_path(result: dict[str, Any] | None) -> str:
    """Pfad aus der Antwort einer ``...GetXxxListPath``-Aktion.

    Der Ausgabeparameter heisst je Dienst anders (``NewX_AVM-DE_HostListPath``,
    ``NewX_AVM-DE_WLANDeviceListPath`` ...). Deshalb zaehlt der erste nicht leere
    Wert, dessen Name auf ``Path`` endet. Ohne Treffer kommt ``""`` zurueck.
    """
    for key, value in (result or {}).items():
        if str(key).lower().endswith("path") and str(value or "").strip():
            return str(value).strip()
    return ""


def parse_wlan_device_list(text: str) -> list[dict[str, str]]:
    """Liest die XML-Liste der WLAN-Geraete (``X_AVM-DE_GetWLANDeviceListPath``).

    Ergebnis ist je ``<Item>`` ein Dictionary mit den Tagnamen als Schluessel
    (``AssociatedDeviceMACAddress``, ``AssociatedDeviceChannel`` ...). Ungueltiges
    XML loest ``xml.etree.ElementTree.ParseError`` aus.
    """
    root = ElementTree.fromstring(text)
    items: list[dict[str, str]] = []
    for item in root.iter("Item"):
        entry = {child.tag: (child.text or "").strip() for child in item}
        if entry:
            items.append(entry)
    return items


def wlan_bands(devices: list[dict[str, str]], service_band: str) -> dict[str, str]:
    """Ordnet die Geraete einer WLAN-Liste ihrem Band zu (``mac_key`` -> Band)."""
    bands: dict[str, str] = {}
    for entry in devices or []:
        key = mac_key(entry.get("AssociatedDeviceMACAddress"))
        if not key:
            continue
        band = device_band(service_band, entry.get("AssociatedDeviceChannel"))
        if band:
            bands[key] = band
    return bands


def apply_bands(
    hosts: list[dict[str, Any]], bands: dict[str, str] | None
) -> list[dict[str, Any]]:
    """Ergaenzt das Funkband anhand des MAC-Schluessels.

    Geraete, die in keiner WLAN-Liste stehen (LAN, offline, oder ein Client
    hinter einem Repeater, den die Box nicht selbst versorgt), behalten ``""``.
    """
    if not bands:
        return hosts
    for host in hosts:
        band = bands.get(mac_key(host["mac"]))
        if band:
            host["band"] = band
    return hosts


def build_hosts(
    raw_hosts: list[dict[str, Any]],
    address_sources: dict[str, dict[str, Any]] | None = None,
    ha_devices: dict[str, dict[str, str]] | None = None,
    last_seen: dict[str, str] | None = None,
    pool: tuple[int, int] | None = None,
    oui: dict[str, str] | None = None,
    bands: dict[str, str] | None = None,
    first_seen: dict[str, str] | None = None,
    mesh_links: dict[str, dict[str, Any]] | None = None,
    notes: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Baut die vollstaendige, sortierte Hostliste fuer das Sensorattribut.

    ``pool`` ist der DHCP-Bereich der Box (siehe ``dhcp_pool``) und dient der
    Einordnung fest/dynamisch. ``oui`` ist die Herstellertabelle (siehe
    ``load_oui``); ohne sie bleibt ``vendor`` leer. ``bands`` ordnet MAC-
    Schluessel dem WLAN-Band zu (siehe ``wlan_bands``); ohne sie bleibt ``band``
    leer.

    Sortiert wird nach IP-Adresse (numerisch). Eintraege ohne MAC-Adresse
    werden verworfen - sie sind Karteileichen der FRITZ!Box und wuerden in
    der Karte nur eine leere Zeile erzeugen.
    """
    hosts = [
        normalize_host(raw)
        for raw in raw_hosts or []
        if normalize_mac(raw.get("MACAddress"))
    ]
    apply_address_sources(hosts, address_sources)
    apply_ha_devices(hosts, ha_devices)
    apply_last_seen(hosts, last_seen)
    apply_first_seen(hosts, first_seen)
    apply_vendors(hosts, oui)
    apply_bands(hosts, bands)
    apply_mesh_links(hosts, mesh_links)
    apply_notes(hosts, notes)
    for host in hosts:
        host["ip_class"] = classify_ip_with_reserved(host, pool)
    hosts.sort(key=lambda host: ip_sort_key(host["ip"]))
    return hosts


def summarize(hosts: list[dict[str, Any]]) -> dict[str, int]:
    """Zaehlt die Kennzahlen, die als eigene Sensorattribute erscheinen."""
    active = sum(1 for host in hosts if host["active"])
    return {
        "total": len(hosts),
        "active": active,
        "inactive": len(hosts) - active,
        "guests": sum(1 for host in hosts if host["guest"]),
        "blocked": sum(1 for host in hosts if host["blocked"]),
        "updates": sum(1 for host in hosts if host["update_available"]),
        # "static" bleibt als Attributname erhalten, zaehlt aber jetzt die
        # fest zugewiesenen Adressen (fest/reserviert).
        "static": sum(1 for host in hosts if host.get("ip_class") == "fixed"),
    }


# ---------------------------------------------------------------------------
# Benannte IP-Bereiche, Baender-Zaehler, DHCP-Auslastung, Adresskonflikte
# (Idee 7 + 8 aus feature-ideen.md)
# ---------------------------------------------------------------------------


def _wildcard_to_regex(pattern: str) -> re.Pattern[str]:
    """Wandelt ein Muster mit ``*``/``?`` in einen verankerten, case-insensitiven
    regulaeren Ausdruck um - dieselbe Syntax wie ``wildcardToRegExp`` im
    Karten-Javascript (Kartenfeld ``ip_filter``), damit IP-Bereiche in den
    Optionen und in der Karte identisch ausgewertet werden.
    """
    body = re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".")
    return re.compile(f"^{body}$", re.IGNORECASE)


def parse_wildcard_filter(value: Any) -> dict[str, list[re.Pattern[str]]] | None:
    """Zerlegt eine Mustervorgabe in Treffer-/Ausschlussmuster.

    Portierung von ``parseIpFilter`` aus der Karte: durch Leerraum, Komma
    oder Semikolon getrennte Muster, ein fuehrendes ``!`` schliesst aus
    (z. B. ``192.168.1.*,!192.168.1.1``). ``None``, wenn nichts zu filtern ist.
    """
    text = (
        ",".join(str(item) for item in value)
        if isinstance(value, (list, tuple))
        else str(value if value is not None else "")
    )
    include: list[re.Pattern[str]] = []
    exclude: list[re.Pattern[str]] = []
    for token in re.split(r"[\s,;]+", text):
        if not token:
            continue
        if token.startswith("!"):
            rest = token[1:]
            if rest:
                exclude.append(_wildcard_to_regex(rest))
        else:
            include.append(_wildcard_to_regex(token))
    if not include and not exclude:
        return None
    return {"include": include, "exclude": exclude}


def ip_matches_filter(ip: Any, filt: dict[str, list[re.Pattern[str]]] | None) -> bool:
    """Prueft eine IP-Adresse gegen ein geparstes Muster (siehe ``ipMatchesFilter``
    im Karten-Javascript). Ohne Treffermuster gilt jede nicht ausgeschlossene
    Adresse als Treffer; eine leere Adresse trifft nie auf ein Treffermuster."""
    if not filt:
        return True
    text = str(ip or "").strip()
    include = filt.get("include") or []
    if include and not any(regex.match(text) for regex in include):
        return False
    return not any(regex.match(text) for regex in filt.get("exclude") or [])


def parse_ip_ranges(text: Any) -> list[dict[str, Any]]:
    """Liest die Options-Angabe benannter IP-Bereiche (Idee 7 aus feature-ideen.md).

    Format: eine Zeile je Bereich, ``Name=Muster`` - das Muster folgt derselben
    Syntax wie das Kartenfeld ``ip_filter`` (siehe ``parse_wildcard_filter``)
    und darf auch mehrere Adressen/Ausschluesse enthalten, z. B.
    ``Drucker=192.168.2.10,192.168.2.11``. Zeilen ohne ``=``, mit leerem
    Namen oder leerem/unbrauchbarem Muster werden uebersprungen; bei
    doppeltem Namen zaehlt die letzte Zeile.
    """
    ranges: dict[str, dict[str, Any]] = {}
    for line in str(text or "").splitlines():
        if "=" not in line:
            continue
        name, _, pattern = line.partition("=")
        name = name.strip()
        pattern = pattern.strip()
        if not name or not pattern:
            continue
        parsed = parse_wildcard_filter(pattern)
        if parsed is None:
            continue
        ranges[name] = {"name": name, "pattern": pattern, "filter": parsed}
    return list(ranges.values())


def count_ip_range(hosts: list[dict[str, Any]], ip_range: dict[str, Any]) -> dict[str, int]:
    """Zaehlt die Geraete eines IP-Bereichs (Idee 7, z. B. "Drucker online: 2 von 3").

    Geraete ohne IP-Adresse treffen nie auf einen Bereich - wie beim
    gleichnamigen Kartenfeld ``ip_filter``.
    """
    filt = ip_range["filter"]
    matching = [
        host for host in hosts if host.get("ip") and ip_matches_filter(host["ip"], filt)
    ]
    active = sum(1 for host in matching if host.get("active"))
    return {"active": active, "total": len(matching)}


def count_band(hosts: list[dict[str, Any]], band: str) -> dict[str, int]:
    """Zaehlt die Geraete eines Funkbands (Idee 7, z. B. "WLAN 5 GHz: 4 Geraete").

    Das Band steht nur, wenn "WLAN-Band je Geraet erfassen" eingeschaltet ist
    und das Geraet direkt an der FRITZ!Box haengt (siehe ``apply_bands``);
    ohne das wird hier fuer jedes Band 0 gezaehlt.
    """
    matching = [host for host in hosts if host.get("band") == band]
    active = sum(1 for host in matching if host.get("active"))
    return {"active": active, "total": len(matching)}


def dhcp_pool_usage(
    hosts: list[dict[str, Any]], pool: tuple[int, int] | None
) -> dict[str, int] | None:
    """Belegung des DHCP-Bereichs (Idee 8, z. B. "Belegte Adressen im Pool: 63 von 100").

    Gezaehlt werden AKTIVE Geraete, deren Adresse im Bereich liegt - eine
    echte Lease-Tabelle liefert TR-064 nicht, ``LANHostConfigManagement1``
    kennt nur Anfang und Ende des Bereichs (siehe ``dhcp_pool``). Ein Geraet,
    das sich abgemeldet hat, zaehlt deshalb bewusst nicht mehr mit, auch wenn
    seine Lease an der Box rein theoretisch noch nicht abgelaufen ist -
    Annahme: das kommt der tatsaechlichen Belegung naeher als jeder Eintrag,
    den die Box jemals in diesem Bereich vergeben hat. ``None`` ohne
    bekannten Bereich (DHCP-Server aus oder (noch) nicht ermittelbar).
    """
    if pool is None:
        return None
    low, high = pool
    total = high - low + 1
    used = 0
    for host in hosts:
        if not host.get("active"):
            continue
        number = ipv4_number(host.get("ip"))
        if number is not None and low <= number <= high:
            used += 1
    return {"total": total, "used": used, "free": max(total - used, 0)}


def ip_conflicts(hosts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Findet IP-Adressen, die mehrere AKTIVE Geraete gleichzeitig melden (Idee 8).

    Ein Adresskonflikt zeigt sich in der Hostliste der FRITZ!Box als zwei
    eigene Eintraege mit identischer ``IPAddress``, die beide ``active`` sind -
    typischerweise, weil ein Geraet mit fest eingestellter Adresse dieselbe
    zusaetzlich per DHCP zugeteilt bekommen hat. Inaktive Geraete mit
    derselben, laengst nicht mehr genutzten Adresse sind KEIN Konflikt und
    werden hier bewusst nicht gezaehlt.
    """
    by_ip: dict[str, list[dict[str, Any]]] = {}
    for host in hosts:
        ip = host.get("ip")
        if not ip or not host.get("active"):
            continue
        by_ip.setdefault(ip, []).append(host)
    return [
        {
            "ip": ip,
            "macs": [host["mac"] for host in matching],
            "names": [host["name"] for host in matching],
        }
        for ip, matching in by_ip.items()
        if len(matching) > 1
    ]


# ---------------------------------------------------------------------------
# WLAN-MAC-Filter ("WLAN-Zugang auf bekannte Geraete beschraenken")
# ---------------------------------------------------------------------------

# Der Filter gilt an der FRITZ!Box fuer die beiden Hauptbaender (2,4 und
# 5 GHz), nicht fuers Gast-WLAN. TR-064 fuehrt ihn je WLANConfiguration-Dienst.
MAC_FILTER_INFO_KEY = "NewMACAddressControlEnabled"
MAC_FILTER_INPUT_KEY = "newmacaddresscontrolenabled"


def is_5ghz_band(band: Any) -> bool:
    """Ob die gemeldete Frequenzangabe (``NewX_AVM-DE_FrequencyBand``) 5 GHz ist."""
    return str(band or "").strip().lower().startswith("5")


def is_mac_filter_band(index: int, info: dict[str, Any]) -> bool:
    """Entscheidet, ob ein WLANConfiguration-Dienst zum MAC-Filter gehoert.

    Dienst 1 ist immer das Hauptband. Dienst 2 zaehlt nur, wenn er sich
    ausdruecklich als 5-GHz-Band ausweist: bei Einzelband-Boxen ist Dienst 2
    das Gast-WLAN, und dort darf nichts umgeschaltet werden. Fehlt die
    Frequenzangabe (aeltere FRITZ!OS), bleibt es bei Dienst 1 - der Filter
    gilt an der Box ohnehin gemeinsam fuer beide Baender.
    """
    if MAC_FILTER_INFO_KEY not in info:
        return False
    if index == 1:
        return True
    return index == 2 and is_5ghz_band(info.get("NewX_AVM-DE_FrequencyBand"))


def set_config_arguments(
    input_names: list[str], info: dict[str, Any], enabled: bool
) -> dict[str, Any]:
    """Baut die Argumente fuer ``WLANConfiguration.SetConfig``.

    ``SetConfig`` verlangt ALLE Einstellungen auf einmal (SSID, Kanal,
    Verschluesselung ...). Damit nichts verstellt wird, werden die aktuellen
    Werte aus ``GetInfo`` unveraendert zurueckgeschrieben und nur der
    MAC-Filter gesetzt. Welche Eingabeargumente es gibt, richtet sich nach
    dem, was die Box selbst meldet (``input_names``); Gross-/Kleinschreibung
    wird dabei ignoriert (``MacAddress...`` vs. ``MACAddress...``).

    Fehlt zu einem Eingabeargument der aktuelle Wert, wird ``ValueError``
    geworfen - lieber gar nichts schreiben als etwas Halbes.
    """
    values = {str(name).lower(): value for name, value in info.items()}
    arguments: dict[str, Any] = {}
    missing: list[str] = []
    for name in input_names:
        key = name.lower()
        if key == MAC_FILTER_INPUT_KEY:
            arguments[name] = bool(enabled)
        elif key in values:
            arguments[name] = values[key]
        else:
            missing.append(name)
    if missing:
        raise ValueError(", ".join(missing))
    if not any(name.lower() == MAC_FILTER_INPUT_KEY for name in arguments):
        raise ValueError("NewMacAddressControlEnabled")
    return arguments


# ---------------------------------------------------------------------------
# Mesh: FRITZ!Box und Repeater als Gruppe
# ---------------------------------------------------------------------------


def mesh_members(
    hosts: list[dict[str, Any]],
    box_name: str,
    box_model: str = "",
    box_ip: str = "",
) -> list[dict[str, Any]]:
    """Die FRITZ!-Geraete des Heimnetzes: zuerst die Box, dann die Repeater.

    Die Box ist in ihrer eigenen Hostliste nicht enthalten; sie antwortet
    aber gerade (sonst gaebe es diese Daten nicht) und gilt deshalb als online.
    Repeater sind die Hosts, die ``build_hosts`` als solche markiert hat - ohne
    gueltige MAC-Adresse werden sie nicht aufgenommen. Die Repeater sind nach
    Namen sortiert, damit die Reihenfolge von Abruf zu Abruf stabil bleibt.
    """
    members: list[dict[str, Any]] = [
        {
            "role": "box",
            "name": box_name,
            "model": box_model,
            "ip": box_ip,
            "mac": None,
            "online": True,
        }
    ]
    repeaters = [
        host for host in hosts if host.get("repeater") and mac_key(host.get("mac"))
    ]
    repeaters.sort(key=lambda h: (str(h.get("name") or "").lower(), str(h.get("mac"))))
    for host in repeaters:
        members.append(
            {
                "role": "repeater",
                "name": host.get("name") or host.get("mac"),
                "model": host.get("model") or "",
                "ip": host.get("ip") or "",
                "mac": host.get("mac"),
                "online": bool(host.get("active")),
            }
        )
    return members


def mesh_summary(members: list[dict[str, Any]]) -> dict[str, Any]:
    """Anzahl und Vollstaendigkeit der Mesh-Gruppe (Box zaehlt mit)."""
    online = sum(1 for member in members if member.get("online"))
    return {
        "total": len(members),
        "online": online,
        "complete": online == len(members),
    }


def mesh_reboot_plan(
    members: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Wer beim "Alle neu starten" drankommt.

    Liefert ``(ziele, uebersprungen)``: Ziele sind die Repeater, die online sind
    und eine IP-Adresse haben; alle anderen (ausgeschaltet oder ohne IP)
    koennen nicht angesprochen werden und landen in ``uebersprungen``. Die
    Box selbst ist nie Teil der Liste - sie kommt immer zuletzt.
    """
    targets: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for member in members:
        if member.get("role") != "repeater":
            continue
        if member.get("online") and member.get("ip"):
            targets.append(member)
        else:
            skipped.append(member)
    return targets, skipped


# ---------------------------------------------------------------------------
# Mesh-Topologie: "Verbunden ueber" und Verbindungsrate (Idee 5 aus
# feature-ideen.md)
# ---------------------------------------------------------------------------


def mesh_link_mbit(kbit_per_s: Any) -> float | None:
    """Rechnet eine Mesh-Verbindungsrate in Mbit/s um (eine Nachkommastelle).

    Die Mesh-Topologie (siehe ``coordinator._fetch_mesh_topology``) liefert
    die Rate ueber ``fritzconnection.lib.fritztopology.Connection`` in
    kbit/s (laut Quelltext dieser Bibliotheksklasse) - ANDERE Einheit als
    ``to_mbit_per_s`` (dort: bit/s fuer die Leitungs-Sync-Rate), deshalb eine
    eigene Umrechnung statt doppelter Verwendung.
    """
    value = as_int(kbit_per_s, default=-1)
    if value < 0:
        return None
    return round(value / 1000, 1)


def slowest_mesh_link(hosts: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Das aktive Geraet mit der aktuell langsamsten Mesh-Verbindungsrate.

    Gedacht als Sensor "Schwaechstes Geraet" aus Idee 5 aus feature-ideen.md -
    bewusst ueber die Verbindungsrate (``link_mbit``, siehe
    ``apply_mesh_links``) statt einer Signalstaerke in dBm: TR-064 liefert
    laut der mit diesem Projekt gepinnten ``fritzconnection``-Bibliothek
    (1.15.1, ``fritzconnection.lib.fritztopology``) keinen Signalstaerke-Wert,
    nur Datenraten (``cur_data_rate_tx``/``cur_data_rate_rx``) - eine
    niedrige Rate ist in der Praxis aber ohnehin der Grund, warum sich
    jemand fuer das "schwaechste Geraet" interessiert. ``None`` ohne
    Geraete mit bekannter Rate (kein Mesh, oder Topologie nicht abrufbar).
    """
    candidates = [
        host
        for host in hosts
        if host.get("active") and isinstance(host.get("link_mbit"), (int, float))
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda host: host["link_mbit"])


def apply_mesh_links(
    hosts: list[dict[str, Any]], links: dict[str, dict[str, Any]] | None
) -> list[dict[str, Any]]:
    """Ergaenzt "verbunden ueber" und die Verbindungsrate anhand des MAC-Schluessels.

    ``links`` kommt von ``FritzboxNetzwerkCoordinator._fetch_mesh_topology``:
    je Geraet mit GENAU EINER aktiven Mesh-Verbindung der Name des Nachbarn
    (FRITZ!Box oder Repeater) und die aktuelle Verbindungsrate. Geraete mit
    mehreren oder keiner aktiven Verbindung (z. B. die Box selbst, oder ein
    Repeater mit mehreren eigenen Clients) bleiben ohne Angabe - "verbunden
    ueber" waere dort nicht aus einem einzelnen Nachbarn eindeutig ablesbar.
    """
    if not links:
        return hosts
    for host in hosts:
        link = links.get(mac_key(host["mac"]))
        if not link:
            continue
        host["connected_via"] = link.get("connected_via") or ""
        host["link_mbit"] = link.get("link_mbit")
    return hosts


# ---------------------------------------------------------------------------
# Verbindungsdaten (Down/Up)
# ---------------------------------------------------------------------------


def to_kbytes_per_s(bytes_per_s: Any) -> float | None:
    """Rechnet Bytes/s in kByte/s um (eine Nachkommastelle).

    Fuer die aktuellen Down-/Upload-Raten der FRITZ!Box gedacht. Ungueltige
    oder fehlende Werte ergeben ``None`` (Sensor wird dann "unbekannt").
    """
    value = as_int(bytes_per_s, default=-1)
    if value < 0:
        return None
    return round(value / 1000, 1)


def to_mbit_per_s(bits_per_s: Any) -> float | None:
    """Rechnet Bit/s in Mbit/s um (eine Nachkommastelle).

    Fuer die maximalen Leitungs-Sync-Raten der FRITZ!Box gedacht.
    """
    value = as_int(bits_per_s, default=-1)
    if value < 0:
        return None
    return round(value / 1_000_000, 1)


# ---------------------------------------------------------------------------
# Neuverbindung (Internet neu einwaehlen)
# ---------------------------------------------------------------------------

# Aktionen, mit denen die Internetverbindung neu aufgebaut wird. Zuerst die
# TR-064-Dienste: sie laufen mit der Anmeldung der Integration (derselben, die
# auch den Neustart erlaubt). Der UPnP-IGD-Dienst ``WANIPConn1`` (das ist
# ``FritzConnection.reconnect()``) wird von manchen FRITZ!Boxen mit Fehler 606
# (nicht autorisiert) abgelehnt, IGD bleibt deshalb nur Rueckfallweg.
# Die tatsaechliche Reihenfolge legt ``reconnect_plan()`` fest: Die Dienste der
# Verbindungsart, die die Box gerade nutzt (IP oder PPP), kommen nach vorn.
RECONNECT_ACTIONS: Final = (
    ("WANIPConnection1", "ForceTermination"),
    ("WANPPPConnection1", "ForceTermination"),
    ("WANIPConn1", "ForceTermination"),
    ("WANPPPConn1", "ForceTermination"),
)

# UPnP-Fehlercodes von ForceTermination (UPnP-IGD-Spezifikation, von AVM
# auch unter TR-064 verwendet):
# 707 DisconnectInProgress - die Verbindung wird bereits getrennt,
# 711 ConnectionAlreadyTerminated - die Verbindung ist schon getrennt.
UPNP_DISCONNECT_IN_PROGRESS: Final = "707"
UPNP_ALREADY_TERMINATED: Final = "711"

# Verbindungsart -> zugehoerige Dienste (TR-064, UPnP-IGD).
_WAN_SERVICES: Final = {
    "WANPPPConnection": ("WANPPPConnection1", "WANPPPConn1"),
    "WANIPConnection": ("WANIPConnection1", "WANIPConn1"),
}

_ERROR_CODE_RE: Final = re.compile(r"errorCode:\s*(\d+)")


def wan_kind(default_connection_service: Any) -> str | None:
    """Verbindungsart aus ``Layer3Forwarding1.GetDefaultConnectionService``.

    Die FRITZ!Box meldet z. B. ``"1.WANPPPConnection.1"`` (DSL mit PPPoE)
    oder ``"1.WANIPConnection.1"`` (Kabel, Glasfaser, IP-Anschluss).
    Ergebnis ist ``"WANPPPConnection"``, ``"WANIPConnection"`` oder ``None``,
    wenn die Angabe fehlt oder unbekannt ist.
    """
    text = str(default_connection_service or "").lower()
    for kind in ("WANPPPConnection", "WANIPConnection"):
        if kind.lower() in text:
            return kind
    return None


def reconnect_plan(kind: str | None) -> list[tuple[str, str, bool]]:
    """Reihenfolge der Neuverbindungs-Versuche als ``(Dienst, Aktion, aktiv)``.

    ``aktiv`` heisst: Der Dienst gehoert zur Verbindungsart, die die Box
    gerade nutzt. Diese Dienste kommen zuerst (TR-064 vor IGD), danach die
    uebrigen in der Grundreihenfolge. Ist die Verbindungsart unbekannt,
    bleibt die Grundreihenfolge und kein Dienst gilt als aktiv.
    """
    active = set(_WAN_SERVICES.get(kind or "", ()))
    ordered = sorted(RECONNECT_ACTIONS, key=lambda item: item[0] not in active)
    return [(service, action, service in active) for service, action in ordered]


def upnp_error_code(error: Any) -> str | None:
    """UPnP-Fehlercode (z. B. ``"707"``) aus einer fritzconnection-Meldung.

    fritzconnection bildet die Meldung aus den XML-Feldern der Antwort, etwa
    ``"UPnPError: errorCode: 707 errorDescription: DisconnectInProgress"``
    (die Teile stehen je nach Version auf eigenen Zeilen). Ohne Code: ``None``.
    """
    match = _ERROR_CODE_RE.search(str(error or ""))
    return match.group(1) if match else None


# ---------------------------------------------------------------------------
# Eigene Notizen, Etiketten und "reserviert"-Markierung (Idee 3 aus
# feature-ideen.md) - nur in Home Assistant gespeichert
# ---------------------------------------------------------------------------

MAX_LABEL_LENGTH: Final = 40
MAX_NOTE_LENGTH: Final = 500


def clean_text(value: Any, limit: int) -> str:
    """Bereinigt eine Nutzereingabe: Steuerzeichen raus, Leerraum glatt, gekuerzt."""
    text = "".join(ch if ch.isprintable() or ch in "\n" else " " for ch in str(value or ""))
    lines = [" ".join(line.split()) for line in text.split("\n")]
    return "\n".join(lines).strip()[:limit]


def make_note_entry(
    label: Any = None, note: Any = None, reserved: Any = None
) -> dict[str, Any] | None:
    """Baut einen Speichereintrag; ``None``, wenn nichts (mehr) zu merken ist.

    Das Etikett ist einzeilig (Zeilenumbrueche werden zu Leerzeichen).
    """
    clean_label = clean_text(str(label or "").replace("\n", " "), MAX_LABEL_LENGTH)
    clean_note = clean_text(note, MAX_NOTE_LENGTH)
    flag = as_bool(reserved)
    if not clean_label and not clean_note and not flag:
        return None
    return {"label": clean_label, "note": clean_note, "reserved": flag}


def apply_notes(
    hosts: list[dict[str, Any]], notes: dict[str, dict[str, Any]] | None
) -> list[dict[str, Any]]:
    """Ergaenzt Etikett, Notiz und "reserviert" anhand des MAC-Schluessels."""
    if not notes:
        return hosts
    for host in hosts:
        entry = notes.get(mac_key(host["mac"]))
        if not entry:
            continue
        host["label"] = str(entry.get("label") or "")
        host["note"] = str(entry.get("note") or "")
        host["reserved"] = bool(entry.get("reserved"))
    return hosts


def load_notes(stored: Any) -> dict[str, dict[str, Any]]:
    """Liest den gespeicherten Bestand tolerant (Fremdformate werden verworfen)."""
    notes: dict[str, dict[str, Any]] = {}
    if not isinstance(stored, dict):
        return notes
    for key, value in stored.items():
        normalized = mac_key(key)
        if not isinstance(value, dict) or not re.fullmatch(r"[0-9a-f]{12}", normalized):
            continue
        entry = make_note_entry(
            value.get("label"), value.get("note"), value.get("reserved")
        )
        if entry:
            notes[normalized] = entry
    return notes


# ---------------------------------------------------------------------------
# Hersteller: eigene Zuordnungen und Aktualisierung aus den IEEE-Registern
# (Idee 4b + 4c aus feature-ideen.md)
# ---------------------------------------------------------------------------

# Download-Adressen der drei IEEE-Register (CSV). Die Adressen stammen aus der
# oeffentlichen IEEE-Dokumentation; sie wurden in der Entwicklungsumgebung
# NICHT abgerufen (kein Zugriff) - siehe release-Notiz "Nicht verifiziert".
IEEE_REGISTER_URLS: Final = (
    ("MA-L", "https://standards-oui.ieee.org/oui/oui.csv", 6),
    ("MA-M", "https://standards-oui.ieee.org/oui28/mam.csv", 7),
    ("MA-S", "https://standards-oui.ieee.org/oui36/oui36.csv", 9),
)

# Plausibilitaetsgrenze: ein MA-L-Register mit weniger Eintraegen ist keine
# gueltige Antwort (Fehlerseite, abgeschnittener Download) und wird NICHT
# uebernommen - sonst wuerde ein kaputter Download die gute Liste ersetzen.
MIN_MA_L_ENTRIES: Final = 20000

_IEEE_SKIP_NAMES: Final = frozenset({"private", "ieee registration authority"})


def parse_ieee_csv(text: str, length: int) -> dict[str, str]:
    """Liest ein IEEE-Register (CSV mit ``Assignment`` und ``Organization Name``).

    ``length`` ist die erwartete Praefixlaenge (6/7/9 Hex-Zeichen); andere
    Zeilen werden uebersprungen. Eintraege mit dem Namen "Private" sind keine
    Auskunft und fehlen deshalb.
    """
    table: dict[str, str] = {}
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header:
        return table
    names = [column.strip().lower() for column in header]
    try:
        i_prefix = names.index("assignment")
        i_name = names.index("organization name")
    except ValueError:
        return table
    for row in reader:
        if len(row) <= max(i_prefix, i_name):
            continue
        prefix = row[i_prefix].strip().upper()
        name = " ".join(row[i_name].split())
        if len(prefix) != length or not re.fullmatch(r"[0-9A-F]+", prefix):
            continue
        if not name or name.lower() in _IEEE_SKIP_NAMES:
            continue
        table[prefix] = sys.intern(name)
    return table


def serialize_oui(table: dict[str, str], header: str = "") -> str:
    """Schreibt eine Tabelle im Dateiformat ``PRAEFIX:Name`` (sortiert)."""
    lines = [f"# {line}" for line in header.splitlines() if line.strip()]
    lines.extend(f"{prefix}:{name}" for prefix, name in sorted(table.items()))
    return "\n".join(lines) + "\n"


def merge_oui(*tables: dict[str, str] | None) -> dict[str, str]:
    """Fuehrt Tabellen zusammen; spaetere gewinnen (Reihenfolge: Basis < Update < eigene)."""
    merged: dict[str, str] = {}
    for table in tables:
        if table:
            merged.update(table)
    return merged


def validate_custom_oui_lines(lines: Any) -> list[int]:
    """Nummern (ab 1) der Zeilen, die weder Kommentar noch gueltiger Eintrag sind.

    Dient dem Hinweis im Protokoll bei Tippfehlern in der eigenen Datei.
    """
    bad: list[int] = []
    for number, line in enumerate(lines, start=1):
        text = str(line).strip()
        if not text or text.startswith("#"):
            continue
        prefix, sep, name = text.partition(":")
        if not sep or not name.strip() or not _OUI_PREFIX.fullmatch(prefix.strip().upper()):
            bad.append(number)
    return bad


# ---------------------------------------------------------------------------
# Netzwerkgeraete als eigene Home-Assistant-Geraete (Idee 9)
# ---------------------------------------------------------------------------


def host_device_selection(
    hosts: list[dict[str, Any]], pattern: Any
) -> list[dict[str, Any]]:
    """Welche Geraete bekommen ein eigenes HA-Geraet?

    ``pattern`` ist dieselbe Platzhalter-Syntax wie der Kartenfilter
    ``ip_filter`` (siehe ``parse_wildcard_filter``). Ein leeres Muster waehlt
    NICHTS aus - bewusst: alle Geraete eines Heimnetzes anzulegen soll eine
    ausdrueckliche Entscheidung sein (``*`` waehlt alle). Repeater haben ihr
    eigenes Geraet und werden hier ausgelassen.
    """
    filt = parse_wildcard_filter(pattern)
    if not filt:
        return []
    return [
        host
        for host in hosts
        if mac_key(host.get("mac"))
        and not host.get("repeater")
        and ip_matches_filter(host.get("ip"), filt)
    ]
