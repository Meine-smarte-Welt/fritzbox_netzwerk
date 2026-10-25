# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 71cdd99b17961dfc6e713a16a03095d0ca7c60e1e36acdb6b5b8e54578344862
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

import heapq
import re
from typing import Any

from fritzconnection.lib.fritztopology import Connection, FritzMeshTopology

from .hosts import BAND_2_4, BAND_5, BAND_6, band_from_channel, mac_key, mesh_link_mbit


def fetch_mesh(
    fc: Any, debug: dict[str, Any] | None = None
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]], dict[str, Any]]:
    """Laedt die Mesh-Topologie einmal und liefert (Verbindungen, Mesh-Geraete, Hauptbox).

    Wie ``fetch_mesh_links``, gibt aber zusaetzlich die FRITZ!-Geraete im Mesh
    zurueck (siehe ``repeaters_from_topology``) - damit auch ein Repeater
    erkannt wird, dessen gemeldetes Modell nicht "Repeater"/"FRITZ!Box" heisst
    (Issue #16) - und die Angaben der Hauptbox (``master_from_topology``).

    Ist ``debug`` ein Dict, wird es mit der anonymisierten Beschreibung der
    Topologie gefuellt (``describe_topology``) - fuer den Diagnose-Export.
    """
    topology = FritzMeshTopology(fc)
    topology.load_topology()
    if debug is not None:
        try:
            description = describe_topology(topology)
        except Exception:  # noqa: BLE001 - reine Diagnose, darf die Auswertung nie kippen
            description = {"error": "Beschreibung der Topologie nicht moeglich"}
        debug.clear()
        debug.update(description)
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


# Kosten einer aktiven Verbindung bei der Wegsuche. Eine Verbindung MIT gemeldeter aktueller
# Datenrate ist glaubwuerdig; eine ohne (Kabel - oder ein veralteter Eintrag, der noch als
# verbunden gilt) zaehlt mehr, damit sie einen echten Weg ueber einen Repeater nicht aussticht.
_COST_ACTIVE = 1.0
_COST_NO_RATE = 2.5


def _role(device: Any) -> str:
    return str(getattr(device, "mesh_role", "") or "").lower()


def _strict_mesh_flags(topology: FritzMeshTopology) -> bool:
    """Ob die Topologie ``is_meshed`` verlaesslich meldet (mindestens ein Repeater ausser der Hauptbox)."""
    return any(getattr(d, "is_meshed", False) and _role(d) != "master" for d in topology.devices)


def _is_hub(device: Any, strict: bool) -> bool:
    """Ob ein Knoten Verkehr weiterleiten kann (Hauptbox, Repeater) - Clients sind nur Endpunkte.

    Ohne verlaessliche ``is_meshed``-Angaben (``strict`` falsch) gilt jeder Knoten als moeglicher
    Zwischenpunkt, wie bisher.
    """
    if not strict:
        return True
    return bool(getattr(device, "is_meshed", False)) or _role(device) in ("master", "slave")


def _has_current_rate(connection: Any) -> bool:
    return any(mesh_link_mbit(getattr(connection, name, None)) for name in ("cur_tx", "cur_rx"))


def _mesh_paths(
    topology: FritzMeshTopology,
) -> tuple[Any, dict[str, float], dict[str, tuple[Any, Any]]]:
    """Guenstigster Weg von der Hauptbox zu jedem Geraet: ``(master, abstand, vorgaenger)``.

    Wegsuche (Dijkstra) ueber die aktiven Verbindungen, ausgehend vom Mesh-Master; der
    ``vorgaenger`` eines Geraets ist ``(nachbar, verbindung)`` - sein Uplink. Nur Hauptbox und
    Repeater leiten weiter, Clients sind Endpunkte. Verbindungen mit aktueller Datenrate sind
    guenstiger als solche ohne (``_COST_*``); bei gleichen Kosten gewinnt die schnellere.
    Ohne Master ist das Ergebnis leer.
    """
    master = next((d for d in topology.devices if _role(d) == "master"), None)
    if master is None:
        return None, {}, {}
    strict = _strict_mesh_flags(topology)
    adjacency: dict[str, list[tuple[Any, Any]]] = {}
    for device in topology.devices:
        for connection in _connected(device):
            target = connection.target
            adjacency.setdefault(device.uid, []).append((target, connection))
            adjacency.setdefault(target.uid, []).append((device, connection))
    distance: dict[str, float] = {master.uid: 0.0}
    parent: dict[str, tuple[Any, Any]] = {}
    best: dict[str, tuple[float, float]] = {}
    heap: list[tuple[float, int, Any]] = [(0.0, 0, master)]
    counter = 1
    while heap:
        dist, _order, current = heapq.heappop(heap)
        if dist > distance.get(current.uid, float("inf")) or not _is_hub(current, strict):
            continue
        for neighbor, connection in adjacency.get(current.uid, []):
            if neighbor.uid == master.uid:
                continue
            cost = _COST_ACTIVE if _has_current_rate(connection) else _COST_NO_RATE
            key = (round(dist + cost, 6), -(link_rate_mbit(connection) or 0.0))
            if neighbor.uid not in best or key < best[neighbor.uid]:
                best[neighbor.uid] = key
                distance[neighbor.uid] = key[0]
                parent[neighbor.uid] = (current, connection)
                heapq.heappush(heap, (key[0], counter, neighbor))
                counter += 1
    return master, distance, parent


def links_from_topology(topology: FritzMeshTopology) -> dict[str, dict[str, Any]]:
    """Baut "verbunden ueber" + Verbindungsrate je Geraet aus einer geladenen Topologie.

    Der Uplink eines Geraets ist der Vorgaenger auf dem guenstigsten Weg von der Hauptbox
    (``_mesh_paths``). Damit bekommt auch ein Repeater mit eigenen Clients - und ein Repeater
    hinter einem anderen Repeater (Kaskade) - seinen Uplink, selbst wenn die Box zusaetzlich
    eine veraltete, als verbunden markierte Verbindung ohne aktuelle Rate zur Hauptbox listet.

    Geraete, die von der Hauptbox aus nicht erreichbar sind (oder eine Topologie ohne
    Master), fallen auf die alte Regel zurueck: genau eine aktive Verbindung ergibt den
    Nachbarn, sonst keine Angabe. Die Hauptbox selbst bekommt nie einen Eintrag.

    Aufgeteilt von ``fetch_mesh_links()``, damit sich dieser Teil - die
    eigentliche Auswertungslogik - mit einer von Hand gebauten Topologie
    testen laesst, ohne eine echte FRITZ!Box zu brauchen.
    """
    links: dict[str, dict[str, Any]] = {}
    master, _distance, parent = _mesh_paths(topology)
    for device in topology.devices:
        keys = _device_keys(device)
        if not keys or (master is not None and device.uid == master.uid):
            continue
        record: dict[str, Any] | None = None
        if device.uid in parent:
            neighbor, connection = parent[device.uid]
            if connection.target.uid != neighbor.uid:
                # Verbindung aus Sicht des Nachbarn gespeichert: Gegenstelle ist
                # dann das eigene Geraet - fuer die Anzeige zaehlt der Nachbar.
                connection = Connection(device, neighbor, connection.interface_link)
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


def describe_topology(topology: FritzMeshTopology) -> dict[str, Any]:
    """Anonymisierte Beschreibung der Mesh-Topologie fuer den Diagnose-Export.

    Ohne Namen und MAC-Adressen: Hauptbox und Repeater als durchnummerierte Knoten
    (Rolle, Modell, ``is_meshed``, Abstand von der Hauptbox, gewaehlter Uplink) und die
    Verbindungen zwischen ihnen (Art, Zustand, aktuelle/maximale Rate). Clients werden
    nur gezaehlt. Damit laesst sich aus einer Meldung ablesen, was die Box wirklich liefert.
    """
    master, distance, parent = _mesh_paths(topology)
    strict = _strict_mesh_flags(topology)
    hubs = [d for d in topology.devices if _is_hub(d, strict)]
    index = {d.uid: number for number, d in enumerate(hubs, 1)}
    nodes: list[dict[str, Any]] = []
    for device in hubs:
        uplink = parent.get(device.uid)
        nodes.append(
            {
                "node": index[device.uid],
                "role": _role(device) or "?",
                "model": str(getattr(device, "model", "") or ""),
                "meshed": bool(getattr(device, "is_meshed", False)),
                "distance": distance.get(device.uid),
                "uplink_node": index.get(uplink[0].uid) if uplink else None,
                "interfaces": sorted({str(getattr(i, "type", "") or "?") for i in device.interfaces}),
            }
        )
    seen: set[Any] = set()
    links: list[dict[str, Any]] = []
    for device in hubs:
        for connection in device.get_connections():
            target = connection.target
            if target.uid not in index:
                continue
            link_id = getattr(connection.interface_link, "uid", None) or tuple(sorted((device.uid, target.uid)))
            if link_id in seen:
                continue
            seen.add(link_id)
            links.append(
                {
                    "from": index[device.uid],
                    "to": index[target.uid],
                    "type": str(getattr(connection, "type", "") or "").upper(),
                    "state": str(getattr(connection, "state", "") or ""),
                    "cur_mbit": max(
                        mesh_link_mbit(getattr(connection, "cur_tx", None)) or 0.0,
                        mesh_link_mbit(getattr(connection, "cur_rx", None)) or 0.0,
                    ),
                    "max_mbit": max(
                        mesh_link_mbit(getattr(connection, "max_tx", None)) or 0.0,
                        mesh_link_mbit(getattr(connection, "max_rx", None)) or 0.0,
                    ),
                }
            )
    return {
        "master_found": master is not None,
        "meshed_flags_reliable": strict,
        "nodes": nodes,
        "links": links,
        "clients": len(topology.devices) - len(hubs),
    }


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
