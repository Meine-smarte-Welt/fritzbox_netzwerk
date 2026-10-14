# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 7ed979872381d56118288020283a357765a2f99c64affc017b34f93bf3477e9a
"""Mesh-Topologie ueber ``fritzconnection.lib.fritztopology`` (Idee 5 aus feature-ideen.md).

Eigenes, von Home Assistant unabhaengiges Modul - wie ``connection.py`` -
damit sich die eigentliche Auswertung ohne laufende Home-Assistant-Instanz
testen laesst (siehe ``tests/test_mesh_topology.py``, das eine synthetische,
aber dem tatsaechlichen fritzconnection-Quelltext nachgebildete Topologie
durchspielt). Nutzt dieselbe, mit diesem Projekt gepinnte Bibliotheksversion
(1.15.1) wie der Rest der Integration - kein eigenes JSON-Parsing von
``X_AVM-DE_GetMeshListPath``.
"""

from __future__ import annotations

import re
from typing import Any

from fritzconnection.lib.fritztopology import FritzMeshTopology

from .hosts import BAND_2_4, BAND_5, BAND_6, band_from_channel, mac_key, mesh_link_mbit


def fetch_mesh(fc: Any) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]]]:
    """Laedt die Mesh-Topologie einmal und liefert (Verbindungen, Mesh-Geraete).

    Wie ``fetch_mesh_links``, gibt aber zusaetzlich die FRITZ!-Geraete im Mesh
    zurueck (siehe ``repeaters_from_topology``) - damit auch ein Repeater
    erkannt wird, dessen gemeldetes Modell nicht "Repeater"/"FRITZ!Box" heisst
    (Issue #16).
    """
    topology = FritzMeshTopology(fc)
    topology.load_topology()
    return links_from_topology(topology), repeaters_from_topology(topology)


def fetch_mesh_links(fc: Any) -> dict[str, dict[str, Any]]:
    """Laedt die Mesh-Topologie von der Box und wertet sie aus.

    ``fc`` ist die ``FritzConnection``-Instanz, die auch ``FritzHosts``
    verwendet (siehe ``coordinator.py``, ``self.fritz_hosts.fc``). Kann jeden
    Fehler von ``FritzMeshTopology.load_topology()`` durchreichen (SOAP-/HTTP-
    Fehler, aber auch - bei unerwartetem Antwortformat - ``KeyError``);
    Fehlerbehandlung obliegt bewusst dem Aufrufer (siehe
    ``coordinator._fetch_mesh_topology``), damit dieses Modul selbst keine
    Logging-/Zustands-Seiteneffekte hat und einfach bleibt.
    """
    topology = FritzMeshTopology(fc)
    topology.load_topology()
    return links_from_topology(topology)


def links_from_topology(topology: FritzMeshTopology) -> dict[str, dict[str, Any]]:
    """Baut "verbunden ueber" + Verbindungsrate je Geraet aus einer geladenen Topologie.

    Nur Geraete mit GENAU EINER aktiven Verbindung (``state == "CONNECTED"``)
    bekommen einen Eintrag: der Nachbar am anderen Ende dieser einen
    Verbindung ist dann eindeutig der Access Point, ueber den das Geraet
    gerade online ist - unabhaengig davon, auf welcher Seite des Links laut
    JSON die Box steht (das uebernehmen ``Connection``/``InterfaceLink`` aus
    der Bibliothek selbst). Geraete mit mehreren aktiven Verbindungen
    (typischerweise die FRITZ!Box selbst oder ein Repeater mit mehreren
    eigenen Clients) bleiben bewusst ohne Angabe - dort waere "verbunden
    ueber" nicht aus einem einzelnen Nachbarn ablesbar, und sie sind in der
    Hostliste ohnehin schon als eigenstaendiger Access Point erkennbar.

    Aufgeteilt von ``fetch_mesh_links()``, damit sich dieser Teil - die
    eigentliche Auswertungslogik - mit einer von Hand gebauten Topologie
    testen laesst, ohne eine echte FRITZ!Box zu brauchen.
    """
    links: dict[str, dict[str, Any]] = {}
    for device in topology.devices:
        key = mac_key(getattr(device, "mac", ""))
        if not key:
            continue
        connected = [
            connection
            for connection in device.get_connections()
            if connection.state == "CONNECTED"
        ]
        if len(connected) != 1:
            continue
        connection = connected[0]
        neighbor_name = str(getattr(connection.target, "name", "") or "").strip()
        if not neighbor_name:
            continue
        links[key] = {
            "connected_via": neighbor_name,
            "link_mbit": mesh_link_mbit(connection.cur_tx),
            "band": link_band(connection),
        }
    return links


_BAND_TOKENS = ((r"(?<![0-9])2G|2[.,]4", BAND_2_4), (r"(?<![0-9])5G", BAND_5), (r"(?<![0-9])6G", BAND_6))


def band_from_interface(interface: Any) -> str:
    """Funkband einer Mesh-Schnittstelle: ``"2.4"``, ``"5"``, ``"6"`` oder ``""``.

    ANNAHME (nicht an echter Hardware geprueft): die Schnittstellennamen der
    AVM-Mesh-Liste tragen das Band, z. B. ``AP:2G:0`` / ``AP:5G:0``. Sonst
    zaehlt - nur fuer WLAN-Schnittstellen - ein gemeldeter Kanal.
    """
    if interface is None:
        return ""
    name = str(getattr(interface, "name", "") or "").upper()
    for pattern, band in _BAND_TOKENS:
        if re.search(pattern, name):
            return band
    if str(getattr(interface, "type", "") or "").upper() == "WLAN":
        for attr in ("current_channel", "channel"):
            band = band_from_channel(getattr(interface, attr, None))
            if band:
                return band
    return ""


def link_band(connection: Any) -> str:
    """Band einer WLAN-Verbindung - bevorzugt von der Seite des Access Points.

    Damit hat auch ein Geraet, das an einem Repeater haengt, ein Band (die
    FRITZ!Box kennt es in ihrer eigenen WLAN-Liste nicht, Issue #21). LAN- und
    andere Verbindungen ergeben ``""``.
    """
    if str(getattr(connection, "type", "") or "").upper() != "WLAN":
        return ""
    link = getattr(connection, "interface_link", None)
    own = getattr(link, "interface", None)
    target_interface = None
    try:
        uid = getattr(link, f"node_interface_{link.target_index}_uid", None)
        for candidate in getattr(connection.target, "interfaces", []):
            if getattr(candidate, "uid", None) == uid:
                target_interface = candidate
                break
    except (AttributeError, KeyError, TypeError):
        target_interface = None
    return band_from_interface(target_interface) or band_from_interface(own)


def repeaters_from_topology(topology: FritzMeshTopology) -> dict[str, dict[str, str]]:
    """FRITZ!-Geraete im Mesh: MAC-Schluessel jeder Schnittstelle -> Name/Modell.

    Als Mesh-Geraet gilt ein Knoten mit ``is_meshed``. Auch die Hauptbox ist
    ein solcher Knoten; der Aufrufer ueberspringt sie ueber ihre IP-Adresse
    (``hosts.apply_mesh_repeaters``). Ein WLAN-Repeater taucht in der Hostliste
    mit der MAC seiner Uplink-Schnittstelle auf, nicht mit der Geraete-MAC -
    deshalb werden alle Schnittstellen-MACs eingetragen.
    """
    found: dict[str, dict[str, str]] = {}
    for device in topology.devices:
        if not getattr(device, "is_meshed", False):
            continue
        if str(getattr(device, "mesh_role", "") or "").lower() == "master":
            continue
        info = {
            "name": str(getattr(device, "name", "") or ""),
            "model": str(getattr(device, "model", "") or ""),
        }
        macs = [getattr(device, "mac", "")]
        macs.extend(getattr(interface, "mac", "") for interface in device.interfaces)
        for mac in macs:
            key = mac_key(mac)
            if key:
                found[key] = info
    return found
