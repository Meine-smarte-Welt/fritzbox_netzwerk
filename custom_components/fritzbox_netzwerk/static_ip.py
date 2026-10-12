# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 9f8a294193626cface773bd670db3ee2dccad50fd38d3f8c323e9b630928644b
"""Feste IPv4-Adresse eines Geraets festlegen (EXPERIMENTELL, 1.8.0).

Entspricht an der FRITZ!Box: Heimnetz -> Netzwerk -> Geraet bearbeiten ->
"Diesem Netzwerkgeraet immer die gleiche IPv4-Adresse zuweisen".

TEIL 1 - ``plan_static_ip`` (belegt durch Tests): reine Pruefung, ohne Zugriff auf
die Box. Sie verhindert doppelt vergebene Adressen (andere Geraete in der
Hostliste, Adresse der Box selbst), prueft Subnetz und Sonderadressen und warnt
bei Adressen im DHCP-Bereich.

TEIL 2 - ``set_static_ip`` (NICHT an einer echten Box geprueft): liest und schreibt
ueber ``data.lua`` ``page=edit_device`` der Weboberflaeche. Die Feldnamen unten
sind ANGENOMMEN, nicht beobachtet. Deshalb schlaegt der Dienst sicher fehl:
- fehlen die erwarteten Schluessel in der Antwort, wird NICHT geschrieben,
- nach dem Schreiben wird erneut gelesen; bei Abweichung wird der Ausgangszustand
  zurueckgeschrieben (falls vorher lesbar) und ein Fehler gemeldet,
- das bisherige Zugangsprofil wird beim Schreiben mitgeschickt, damit es nicht
  verloren geht.
Die Adresse gilt erst, wenn das Geraet seine Verbindung erneuert (Neustart bzw.
WLAN/LAN neu verbinden).

Das Modul hat keine Home-Assistant- und keine fritzconnection-Importe.
"""
from __future__ import annotations

import ipaddress
from typing import Any

from .hosts import mac_key, normalize_mac
from .webui import (
    TIMEOUT,
    _find_device,
    data_lua,
    login,
    logout,
    parse_device_profile,
)

# --- ANGENOMMENE Feldnamen der Weboberflaeche (nicht beobachtet) -------------
READ_PATH = ("data", "vars", "dev", "ipv4")
READ_FLAG_KEY = "dhcp"  # "1"/"on"/true, wenn die feste Zuweisung aktiv ist
READ_IP_KEYS = ("current", "ip")
WRITE_FLAG_FIELD = "dhcp"  # Formularfeld, Wert "on"
WRITE_IP_FIELD = "ipv4"

NEEDS_RESTART = (
    "Die neue Adresse gilt erst, wenn das Gerät neu gestartet bzw. neu mit dem "
    "Netzwerk verbunden wurde."
)


class StaticIpError(ValueError):
    """Pruefung oder Schreiben der festen IP-Adresse ist fehlgeschlagen."""


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in ("1", "on", "true", "yes")


def _v4(value: Any, what: str) -> ipaddress.IPv4Address:
    try:
        return ipaddress.IPv4Address(str(value).strip())
    except ValueError as err:
        raise StaticIpError(f"{what} ist keine gültige IPv4-Adresse: {value!r}") from err


def plan_static_ip(
    hosts: list[dict[str, Any]],
    mac: str,
    ip: Any,
    *,
    box_ip: str | None = None,
    netmask: str | None = None,
    pool: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Prueft eine gewuenschte feste Adresse (ohne Zugriff auf die Box).

    Wirft ``StaticIpError`` bei Doppelvergabe oder ungueltiger Adresse. Gibt
    ``{"mac", "name", "current_ip", "ip", "unchanged", "warnings"}`` zurueck.
    """
    key = mac_key(mac)
    host = next((h for h in hosts if mac_key(h.get("mac")) == key), None)
    if host is None:
        raise StaticIpError(f"Gerät {mac} ist nicht in der Geräteliste")
    target = _v4(ip, "Die Adresse")
    if (
        target.is_unspecified
        or target.is_loopback
        or target.is_multicast
        or target.is_link_local
        or target.is_reserved
    ):
        raise StaticIpError(f"{target} ist als Geräteadresse nicht zulässig")

    warnings: list[str] = []
    if box_ip:
        if target == _v4(box_ip, "Die Adresse der FRITZ!Box"):
            raise StaticIpError(f"{target} ist die Adresse der FRITZ!Box selbst")
        if netmask:
            network = ipaddress.IPv4Network(f"{box_ip}/{netmask}", strict=False)
            if target not in network:
                raise StaticIpError(f"{target} liegt nicht im Heimnetz {network}")
            if target in (network.network_address, network.broadcast_address):
                raise StaticIpError(f"{target} ist Netz- bzw. Broadcast-Adresse von {network}")
    else:
        warnings.append("Heimnetz der Box nicht ermittelbar - Subnetz nicht geprüft")

    for other in hosts:
        if mac_key(other.get("mac")) == key or str(other.get("ip") or "") != str(target):
            continue
        who = other.get("name") or other.get("mac") or "ein anderes Gerät"
        if other.get("active") or other.get("ip_class") == "fixed" or other.get("reserved"):
            raise StaticIpError(f"{target} ist schon vergeben an {who}")
        warnings.append(f"{target} war zuletzt {who} zugeteilt (derzeit offline)")

    if pool is not None:
        number = int(target)
        if pool[0] <= number <= pool[1]:
            warnings.append(
                "Die Adresse liegt im DHCP-Bereich der Box; besser eine Adresse außerhalb wählen"
            )

    current = str(host.get("ip") or "")
    return {
        "mac": normalize_mac(mac),
        "name": host.get("name") or "",
        "current_ip": current,
        "ip": str(target),
        "unchanged": current == str(target) and host.get("ip_class") == "fixed",
        "warnings": warnings,
    }


def parse_static_state(payload: Any) -> dict[str, Any]:
    """Liest (feste Zuweisung aktiv?, Adresse) aus ``edit_device``; wirft bei fremdem Aufbau."""
    node: Any = payload
    for key in READ_PATH:
        node = node.get(key) if isinstance(node, dict) else None
    if not isinstance(node, dict) or READ_FLAG_KEY not in node:
        raise StaticIpError(
            "Die Einstellung 'immer die gleiche IPv4-Adresse' ist in der Antwort der "
            "Weboberfläche nicht zu finden (FRITZ!OS anders aufgebaut als angenommen) - "
            "es wurde nichts geändert"
        )
    ip = next((str(node[k]).strip() for k in READ_IP_KEYS if node.get(k)), "")
    return {"fixed": _truthy(node[READ_FLAG_KEY]), "ip": ip}


def _read(session: Any, base: str, sid: str, uid: str) -> tuple[dict[str, Any], Any]:
    payload = data_lua(session, base, sid, "edit_device", dev=uid)
    return parse_static_state(payload), payload


def _post(session: Any, base: str, sid: str, device: dict[str, str], fields: dict[str, str]) -> None:
    form = {
        "sid": sid,
        "dev": device["uid"],
        "dev_name": device["name"],
        "page": "edit_device",
        "apply": "true",
    }
    form.update(fields)
    response = session.post(f"{base}/data.lua", data=form, timeout=TIMEOUT)
    if not response.ok:
        raise StaticIpError(f"data.lua (edit_device): HTTP {response.status_code}")


def set_static_ip(
    session: Any,
    base: str,
    user: str,
    password: str,
    mac: str,
    ip: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Schreibt die feste Adresse (vorher lesen, nachher pruefen, bei Abweichung zurueck).

    ``dry_run`` liest nur und meldet, was geschrieben wuerde.
    """
    sid = login(session, base, user, password)
    try:
        device = _find_device(session, base, sid, mac)
        before, payload = _read(session, base, sid, device["uid"])
        profile = parse_device_profile(payload)
        if dry_run:
            return {"before": before, "device": device["name"]}
        extra = {"kisi_profile": profile} if profile else {}
        _post(session, base, sid, device, {WRITE_FLAG_FIELD: "on", WRITE_IP_FIELD: ip, **extra})
        after, _p = _read(session, base, sid, device["uid"])
        if not after["fixed"] or after["ip"] != ip:
            restored = _restore(session, base, sid, device, before, extra)
            raise StaticIpError(
                "Die FRITZ!Box hat die feste Adresse nicht übernommen "
                f"(jetzt: {after['ip'] or 'unbekannt'}, fest: {after['fixed']}). "
                + ("Ausgangszustand wiederhergestellt." if restored else
                   "Ausgangszustand konnte NICHT bestätigt werden - bitte in der Box prüfen.")
            )
        return {"before": before, "after": after, "device": device["name"]}
    finally:
        logout(session, base, sid)


def _restore(
    session: Any, base: str, sid: str, device: dict[str, str], before: dict[str, Any], extra: dict[str, str]
) -> bool:
    fields: dict[str, str] = dict(extra)
    if before["fixed"]:
        fields.update({WRITE_FLAG_FIELD: "on", WRITE_IP_FIELD: before["ip"]})
    try:
        _post(session, base, sid, device, fields)
        now, _p = _read(session, base, sid, device["uid"])
    except (ValueError, OSError):
        return False
    return now["fixed"] == before["fixed"] and (not before["fixed"] or now["ip"] == before["ip"])
