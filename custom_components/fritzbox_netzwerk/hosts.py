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

from typing import Any

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
    """Erkennt einen AVM-Repeater anhand der gemeldeten Modellbezeichnung.

    Die FRITZ!Box traegt bei eigenen Geraeten im Mesh das Modell ein, z. B.
    ``FRITZ!Repeater 1200 AX`` oder ``FRITZ!Repeater 6000``. Erkannt wird
    ausschliesslich das, was das Modell ausdruecklich als Repeater ausweist -
    es wird nichts aus dem Hostnamen geraten.
    """
    return "repeater" in str(model or "").strip().lower()


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
        "active": as_bool(raw.get("Active")),
        "connection": kind,
        "connection_label": connection_label(kind, port, guest),
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


def classify_ip(host: dict[str, Any]) -> str | None:
    """Ermittelt, wie die IP-Adresse eines Geraets vergeben ist.

    Hintergrund: Die FRITZ!Box meldet auch eine dauerhaft zugewiesene
    ("fixierte") IPv4 als AddressSource=DHCP - nur die Lease-Restzeit
    unterscheidet wirklich. Ein Geraet aus dem DHCP-Pool hat eine
    ablaufende Lease, eine feste/reservierte Adresse nicht. Fuer Nutzer
    zaehlt genau diese Unterscheidung, nicht das rohe DHCP/Static der Box.

    Rueckgabe:
    - "none"   : Geraet ohne IP-Adresse (z. B. einfacher Switch, Powerline)
    - "dynamic": aus dem DHCP-Pool zugewiesen (Lease laeuft ab)
    - "fixed"  : fest zugewiesen bzw. reserviert
    - None     : noch nicht bekannt (IP-Typ-Erfassung aus oder noch nicht gelaufen)
    """
    if not host.get("ip"):
        return "none"
    lease = host.get("lease_time_remaining")
    if isinstance(lease, int) and lease > 0:
        return "dynamic"
    if host.get("address_source") or host.get("static_ip") is not None:
        return "fixed"
    return None


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


def build_hosts(
    raw_hosts: list[dict[str, Any]],
    address_sources: dict[str, dict[str, Any]] | None = None,
    ha_devices: dict[str, dict[str, str]] | None = None,
    last_seen: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Baut die vollstaendige, sortierte Hostliste fuer das Sensorattribut.

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
    for host in hosts:
        host["ip_class"] = classify_ip(host)
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
