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

from typing import Any

from fritzconnection.lib.fritztopology import FritzMeshTopology

from .hosts import mac_key, mesh_link_mbit


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
        }
    return links
