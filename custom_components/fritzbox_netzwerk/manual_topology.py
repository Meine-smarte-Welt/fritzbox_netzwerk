# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): c2cd86279da64a458c8078e0158fd85ea3ab130b995b10bb1e718c0ddade1298
"""Manuelle Mesh-Zuordnung (2.2.0): Mutter-Kind-Verbindungen per Hand festlegen.

Die FRITZ!Box meldet ihre Topologie nur fuer AVM-Mesh-Geraete verlaesslich. Kaskadierte
FRITZ!Boxen, verwaltete Switches oder Repeater-Ketten stimmen daher in der Karte nicht
immer (Issues #37, #41). Dieses Modul legt eine Schicht darueber, die der Nutzer in der
Karte per Drag und Drop (oder im Geraete-Popup) bestimmt:

* ``parents``: Kind -> Mutter. Das Kind ist ein Client, ein Repeater oder ein Switch, die
  Mutter die Box, ein Repeater oder ein Switch (Zwischenstation).
* ``hubs``: Geraete, die der Nutzer selbst zur Zwischenstation (Switch) erklaert hat, z. B.
  eine kaskadierte FRITZ!Box. Sie erscheinen in der Karte als Station und nehmen Kinder auf.

Gespeichert wird nur in Home Assistant, die FRITZ!Box wird nie veraendert. Das Modul hat
keine Home-Assistant-Importe und ist mit einfachen Dictionaries pruefbar.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .hosts import apply_mesh_switches, mac_key

ROOT_REF = "box"
MAX_ENTRIES = 500
STORAGE_VERSION = 1

# Felder, in denen ein Geraet seine automatisch erkannte Zuordnung ablegt, damit sie sich
# nach dem Aufheben einer manuellen Zuordnung ohne neue Abfrage wiederherstellen laesst.
_AUTO_FIELDS = (("via_id", "auto_via_id"), ("connected_via", "auto_connected_via"), ("link_mbit", "auto_link_mbit"))


def _clean_ref(value: Any) -> str:
    """Bereinigt eine Kennung: ``box`` bleibt, sonst nur Kleinbuchstaben und Ziffern."""
    text = str(value or "").strip().lower()
    if text == ROOT_REF:
        return ROOT_REF
    return mac_key(text)


def empty_overrides() -> dict[str, Any]:
    return {"parents": {}, "hubs": []}


def load_overrides(stored: Any) -> dict[str, Any]:
    """Liest den gespeicherten Bestand tolerant; Unbrauchbares wird verworfen."""
    result = empty_overrides()
    if not isinstance(stored, dict):
        return result
    parents = stored.get("parents")
    if isinstance(parents, dict):
        for child, parent in list(parents.items())[:MAX_ENTRIES]:
            c, p = _clean_ref(child), _clean_ref(parent)
            if c and p and c != ROOT_REF and c != p:
                result["parents"][c] = p
    hubs = stored.get("hubs")
    if isinstance(hubs, list):
        for item in hubs[:MAX_ENTRIES]:
            ref = _clean_ref(item)
            if ref and ref != ROOT_REF and ref not in result["hubs"]:
                result["hubs"].append(ref)
    return result


def dump_overrides(overrides: dict[str, Any]) -> dict[str, Any]:
    return {"parents": dict(overrides.get("parents", {})), "hubs": list(overrides.get("hubs", []))}


def host_ref(host: dict[str, Any]) -> str:
    """Kennung eines Geraets: bei Zwischenstationen die Mesh-Kennung, sonst die MAC."""
    return _clean_ref(host.get("mesh_id")) or mac_key(host.get("mac"))


def member_ref(member: dict[str, Any]) -> str:
    """Kennung einer Station der Mesh-Gruppe (Box: ``box``)."""
    if member.get("role") == "box":
        return ROOT_REF
    return _clean_ref(member.get("mesh_id")) or mac_key(member.get("mac"))


def _member_aliases(member: dict[str, Any]) -> set[str]:
    aliases = {member_ref(member), _clean_ref(member.get("mesh_id")), mac_key(member.get("mac"))}
    aliases.update(_clean_ref(key) for key in member.get("keys") or [])
    aliases.discard("")
    return aliases


def merge_manual_hubs(
    hosts: list[dict[str, Any]],
    switches: list[dict[str, Any]] | None,
    hub_refs: list[str],
) -> list[dict[str, Any]]:
    """Switch-Liste samt der vom Nutzer erklaerten Zwischenstationen (Kopie, Eingabe bleibt)."""
    result = [dict(switch) for switch in switches or []]
    known: set[str] = set()
    for switch in result:
        known.add(_clean_ref(switch.get("id")))
        known.update(_clean_ref(key) for key in switch.get("keys") or [])
    for host in hosts:
        key = mac_key(host.get("mac"))
        if not key or key not in hub_refs or key in known or host.get("repeater"):
            continue
        model = str(host.get("model") or "")
        result.append(
            {
                "id": key,
                "name": host.get("label") or host.get("name") or host.get("mac") or "Switch",
                "model": model,
                "mac": host.get("mac") or "",
                "keys": [key],
                "via_id": host.get("auto_via_id", host.get("via_id")) or "",
                "connected_via": host.get("auto_connected_via", host.get("connected_via")) or "",
                "link_mbit": host.get("auto_link_mbit", host.get("link_mbit")),
                "type": str(host.get("link_type") or "LAN"),
                # Eine kaskadierte FRITZ!Box bekommt in der Karte das Router-Symbol (Issue #41).
                "cascade": model.lower().startswith(("fritz!box", "fritzbox")),
                "manual": True,
            }
        )
        known.add(key)
    return result


def _restore_auto(hosts: list[dict[str, Any]]) -> None:
    """Stellt die automatisch erkannte Zuordnung wieder her (nach frueherer manueller Zuordnung)."""
    for host in hosts:
        if host.get("manual_hub"):
            # Eine fruehere manuelle Zwischenstation zuruecknehmen; apply_mesh_switches setzt sie neu.
            host.pop("manual_hub", None)
            host.pop("switch", None)
            if host.get("mesh_id") == mac_key(host.get("mac")):
                host.pop("mesh_id", None)
        if "manual_parent" not in host and "auto_via_id" not in host:
            continue
        for field, backup in _AUTO_FIELDS:
            if backup in host:
                host[field] = host.pop(backup)
        host.pop("manual_parent", None)


def would_cycle(members: list[dict[str, Any]], child: str, parent: str) -> bool:
    """Ob ``parent`` unterhalb von ``child`` haengt (oder gleich ist) - dann entstuende ein Kreis."""
    child, parent = _clean_ref(child), _clean_ref(parent)
    if not child or child == parent:
        return True
    by_alias: dict[str, dict[str, Any]] = {}
    for member in members:
        for alias in _member_aliases(member):
            by_alias.setdefault(alias, member)
    by_id = {m.get("mesh_id"): m for m in members if m.get("mesh_id")}
    node = by_alias.get(parent)
    seen: set[str] = set()
    while node is not None:
        ref = member_ref(node)
        if ref == child or child in _member_aliases(node):
            return True
        if ref in seen or node.get("role") == "box":
            return False
        seen.add(ref)
        node = by_id.get(node.get("via_id")) or by_alias.get(_clean_ref(node.get("via_id")))
    return False


def apply_manual_topology(
    hosts: list[dict[str, Any]],
    switches: list[dict[str, Any]] | None,
    overrides: dict[str, Any],
    members_factory: Callable[[list[dict[str, Any]], list[dict[str, Any]]], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Legt die manuelle Zuordnung ueber die erkannte Topologie.

    Aendert ``hosts`` an Ort und Stelle und gibt die wirksame Switch-Liste zurueck (der
    Cache des Koordinators bleibt unveraendert). ``members_factory(hosts, switches)`` baut
    die Gruppe wie ``hosts.mesh_members``; sie dient hier nur zum Nachschlagen der Muetter.
    """
    _restore_auto(hosts)
    effective = merge_manual_hubs(hosts, switches, list(overrides.get("hubs", [])))
    apply_mesh_switches(hosts, effective)
    for host in hosts:
        if host.get("switch") and mac_key(host.get("mac")) in overrides.get("hubs", []):
            host["manual_hub"] = True
    for switch in effective:
        switch.pop("manual_parent", None)

    parents: dict[str, str] = overrides.get("parents", {})
    if not parents:
        return effective

    members = members_factory(hosts, effective)
    member_by_alias: dict[str, dict[str, Any]] = {}
    for member in members:
        for alias in _member_aliases(member):
            member_by_alias.setdefault(alias, member)
    host_by_alias: dict[str, dict[str, Any]] = {}
    for host in hosts:
        for alias in {host_ref(host), mac_key(host.get("mac")), _clean_ref(host.get("mesh_id"))} - {""}:
            host_by_alias.setdefault(alias, host)
    switch_by_alias: dict[str, dict[str, Any]] = {}
    for switch in effective:
        for alias in {_clean_ref(switch.get("id")), *(_clean_ref(k) for k in switch.get("keys") or [])} - {""}:
            switch_by_alias.setdefault(alias, switch)

    # Der Reihe nach anwenden; ein Eintrag, der einen Kreis erzeugen wuerde, wird uebersprungen.
    for child_key, parent_key in parents.items():
        mother = member_by_alias.get(parent_key)
        if mother is None:
            continue
        host = host_by_alias.get(child_key)
        switch = switch_by_alias.get(child_key)
        if host is None and switch is None:
            continue
        child_member = member_by_alias.get(child_key)
        if child_member is not None and would_cycle(members, child_member.get("mesh_id") or child_key, member_ref(mother)):
            continue
        via_id = str(mother.get("mesh_id") or "")
        via_name = str(mother.get("name") or "")
        if host is not None:
            for field, backup in _AUTO_FIELDS:
                host.setdefault(backup, host.get(field))
            host.update({"via_id": via_id, "connected_via": via_name, "manual_parent": True})
            if host.get("auto_via_id") != via_id or host.get("auto_connected_via") != via_name:
                host["link_mbit"] = None
        if switch is not None:
            switch.update(
                {
                    "auto_via_id": switch.get("via_id") or "",
                    "auto_connected_via": switch.get("connected_via") or "",
                    "via_id": via_id,
                    "connected_via": via_name,
                    "link_mbit": None,
                    "manual_parent": True,
                }
            )
        # Die Gruppe fuer die naechste Pruefung auf Kreise aktuell halten.
        if child_member is not None:
            child_member["via_id"] = via_id
            child_member["connected_via"] = via_name
    return effective
