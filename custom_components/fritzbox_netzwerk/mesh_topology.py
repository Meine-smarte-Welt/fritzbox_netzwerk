# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 46a9c021de134afd3841ad370dc7d486323e55eb65504f493a7cb28aa98fd038
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
from collections import deque
from typing import Any

from fritzconnection.lib.fritztopology import Connection, FritzMeshTopology

from .hosts import BAND_2_4, BAND_5, BAND_6, band_from_channel, mac_key, mesh_link_mbit


def fetch_mesh(
    fc: Any,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]], dict[str, Any]]:
    """Laedt die Mesh-Topologie einmal und liefert (Verbindungen, Mesh-Geraete, Hauptbox).

    Wie ``fetch_mesh_links``, gibt aber zusaetzlich die FRITZ!-Geraete im Mesh
    zurueck (siehe ``repeaters_from_topology``) - damit auch ein Repeater
    erkannt wird, dessen gemeldetes Modell nicht "Repeater"/"FRITZ!Box" heisst
    (Issue #16) - und die Angaben der Hauptbox (``master_from_topology``).
    """
    topology = FritzMeshTopology(fc)
    topology.load_topology()
    return (
        links_from_topology(topology),
        repeaters_from_topology(topology),
        master_from_topology(topology),
    )


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


def _device_keys(device: Any) -> list[str]:
    """MAC-Schluessel eines Mesh-Geraets: Geraete-MAC und alle Schnittstellen-MACs.

    Ein WLAN-Repeater steht in der Hostliste der Box mit der MAC seiner
    Uplink-Schnittstelle, nicht mit der Geraete-MAC - ohne die Schnittstellen-
    MACs liesse sich seine Verbindung nicht zuordnen.
    """
    keys: list[str] = []
    for mac in [getattr(device, "mac", "")] + [
        getattr(interface, "mac", "") for interface in getattr(device, "interfaces", [])
    ]:
        key = mac_key(mac)
        if key and key not in keys:
            keys.append(key)
    return keys


def device_id(device: Any) -> str:
    """Kennung eines Mesh-Geraets (MAC-Schluessel seiner Geraete-MAC)."""
    return mac_key(getattr(device, "mac", ""))


def link_rate_mbit(connection: Any) -> float | None:
    """Verbindungsrate in Mbit/s: aktuelle Rate, sonst die maximale.

    ANNAHME (nicht an echter Hardware geprueft): Bei Kabelverbindungen und
    manchen Repeatern fehlt die aktuelle Rate (``cur_data_rate_*``); die
    maximale Rate (``max_data_rate_*``) ist dann die beste verfuegbare Angabe.
    Eine Rate von 0 gilt als unbekannt.
    """
    for name in ("cur_tx", "cur_rx", "max_tx", "max_rx"):
        value = mesh_link_mbit(getattr(connection, name, None))
        if value:
            return value
    return None


def _connected(device: Any) -> list[Any]:
    return [c for c in device.get_connections() if c.state == "CONNECTED"]


def _link_record(connection: Any) -> dict[str, Any]:
    target = connection.target
    return {
        "connected_via": str(getattr(target, "name", "") or "").strip(),
        "via_id": device_id(target),
        "link_mbit": link_rate_mbit(connection),
        "band": link_band(connection),
        "type": str(getattr(connection, "type", "") or "").upper(),
    }


def _mesh_depths(topology: FritzMeshTopology) -> tuple[dict[str, int], dict[str, list[tuple[Any, Any]]]]:
    """Abstand jedes Geraets von der Hauptbox und die Nachbarschaft (beide Richtungen).

    Breitensuche ueber die aktiven Verbindungen, ausgehend vom Mesh-Master.
    Ein Repeater hinter einem Repeater hat so Abstand 2, ein Client daran 3.
    Ohne Master ist das Ergebnis leer.
    """
    master = next(
        (d for d in topology.devices if str(getattr(d, "mesh_role", "") or "").lower() == "master"),
        None,
    )
    adjacency: dict[str, list[tuple[Any, Any]]] = {}
    for device in topology.devices:
        for connection in _connected(device):
            target = connection.target
            adjacency.setdefault(device.uid, []).append((target, connection))
            adjacency.setdefault(target.uid, []).append((device, connection))
    if master is None:
        return {}, adjacency
    depth = {master.uid: 0}
    queue = deque([master])
    while queue:
        current = queue.popleft()
        for neighbor, _connection in adjacency.get(current.uid, []):
            if neighbor.uid not in depth:
                depth[neighbor.uid] = depth[current.uid] + 1
                queue.append(neighbor)
    return depth, adjacency


def links_from_topology(topology: FritzMeshTopology) -> dict[str, dict[str, Any]]:
    """Baut "verbunden ueber" + Verbindungsrate je Geraet aus einer geladenen Topologie.

    Der Nachbar, ueber den ein Geraet gerade online ist, ist der mit dem
    kleineren Abstand zur Hauptbox (Breitensuche vom Mesh-Master aus). Damit
    bekommt auch ein Repeater mit eigenen Clients - und ein Repeater hinter
    einem anderen Repeater (Kaskade) - seinen Uplink; frueher blieben alle
    Geraete mit mehreren aktiven Verbindungen ohne Angabe.

    Geraete, die von der Hauptbox aus nicht erreichbar sind (oder eine
    Topologie ohne Master), fallen auf die alte Regel zurueck: genau eine
    aktive Verbindung ergibt den Nachbarn, sonst keine Angabe. Die Hauptbox
    selbst bekommt nie einen Eintrag.

    Aufgeteilt von ``fetch_mesh_links()``, damit sich dieser Teil - die
    eigentliche Auswertungslogik - mit einer von Hand gebauten Topologie
    testen laesst, ohne eine echte FRITZ!Box zu brauchen.
    """
    links: dict[str, dict[str, Any]] = {}
    depth, adjacency = _mesh_depths(topology)
    for device in topology.devices:
        keys = _device_keys(device)
        if not keys:
            continue
        own = depth.get(device.uid)
        if own == 0:
            continue
        record: dict[str, Any] | None = None
        if own is not None:
            candidates = [
                (neighbor, connection)
                for neighbor, connection in adjacency.get(device.uid, [])
                if depth.get(neighbor.uid, own) < own
            ]
            if candidates:
                best = min(
                    candidates,
                    key=lambda item: (
                        depth[item[0].uid],
                        -(link_rate_mbit(item[1]) or 0.0),
                    ),
                )
                connection = best[1]
                if connection.target.uid != best[0].uid:
                    # Verbindung aus Sicht des Nachbarn gespeichert: Gegenstelle ist
                    # dann das eigene Geraet - fuer die Anzeige zaehlt der Nachbar.
                    connection = Connection(device, best[0], connection.interface_link)
                record = _link_record(connection)
        else:
            connected = _connected(device)
            if len(connected) == 1:
                record = _link_record(connected[0])
        if record is None or not (record["connected_via"] or record["via_id"]):
            continue
        for key in keys:
            links[key] = record
    return links


def master_from_topology(topology: FritzMeshTopology) -> dict[str, Any]:
    """Angaben der Hauptbox (Mesh-Master): ``id``, ``name``, ``model``, ``keys``.

    Leer, wenn die Topologie keinen Master meldet.
    """
    for device in topology.devices:
        if str(getattr(device, "mesh_role", "") or "").lower() == "master":
            return {
                "id": device_id(device),
                "name": str(getattr(device, "name", "") or "").strip(),
                "model": str(getattr(device, "model", "") or "").strip(),
                "keys": _device_keys(device),
            }
    return {}


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
            "id": device_id(device),
        }
        for key in _device_keys(device):
            found[key] = info
    return found
