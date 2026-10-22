# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): b87deb8df23841672cfdbfecd33ed27dfc9942011dd9132050533fcc0e46c6cb
"""Feste IPv4-Adresse eines Geraets festlegen (EXPERIMENTELL, ab 2.0.0 ueber REST).

Entspricht an der FRITZ!Box: Heimnetz -> Netzwerk -> Geraet bearbeiten ->
"Diesem Netzwerkgeraet immer die gleiche IPv4-Adresse zuweisen".

TEIL 1 - ``plan_static_ip`` (belegt durch Tests): reine Pruefung, ohne Zugriff auf
die Box. Sie verhindert doppelt vergebene Adressen (andere Geraete in der
Hostliste, Adresse der Box selbst), prueft Subnetz und Sonderadressen und warnt
bei Adressen im DHCP-Bereich.

TEIL 2 - ``set_static_ip`` (NICHT an einer echten Box geprueft): schreibt ueber
die REST-Schnittstelle der Weboberflaeche, wie sie ein Fremdprojekt fuer
FRITZ!OS 8.25 beschreibt (jvejmelka/fritzbox-static-lease): ``PUT
/api/v0/generic/landevice/landevice/<UID>`` mit dem Kopf ``AUTHORIZATION:
AVM-SID <sid>`` und dem JSON-Koerper ``{"static_dhcp": "1"}``; die gewuenschte
Adresse kommt als ``"ip"`` hinzu (dieses Feld ist auch dort fuer 8.25 ungeprueft).
Bis 1.9.x nutzte die Integration stattdessen angenommene Formularfelder von
``data.lua`` (Issue "Umbenennung der IP-Adresse funktioniert nicht"): die Felder
waren nie beobachtet und wurden von der Box nicht uebernommen. Der alte Weg bleibt
nur als Rueckfall, wenn die REST-Route mit einem HTTP-Fehler antwortet (aelteres
FRITZ!OS).

Sicherheitsnetz: Schluessel der Antworten werden nicht geraten. Nach dem Schreiben
wird der Zustand nachgelesen (``query.lua``, ersatzweise REST/``edit_device``).
- Zustand "nicht fest" nach dem Schreiben: Fehler, bei vorher aktiver Zuweisung wird
  der Ausgangszustand zurueckgeschrieben. Ein HTTP 200 allein gilt nicht als Erfolg
  (nach der Beschreibung des Fremdprojekts verwirft die Box Aenderungen ohne
  Fehlermeldung, wenn fuer das Benutzerkonto die Zusatzbestaetigung aktiv ist).
- Nicht nachlesbar: die Antwort enthaelt dann ``verified: False`` und einen Hinweis.
Die Adresse gilt erst, wenn das Geraet seine Verbindung erneuert (Neustart bzw.
WLAN/LAN neu verbinden).

Das Modul hat keine Home-Assistant- und keine fritzconnection-Importe.
"""
from __future__ import annotations

import ipaddress
from typing import Any

from .dns_settings import (
    ConfirmationRequired,
    DnsSettingsError,
    SessionExpired,
    _is_http_error,
    api_request,
)
from .hosts import mac_key, normalize_mac
from .webui import (
    LANDEVICE_QUERY,
    TIMEOUT,
    _find_device,
    data_lua,
    login,
    logout,
    parse_device_profile,
    parse_landevice_list,
    query_lua,
)
from .webui import normalize_mac as plain_mac

# --- REST-Route der Weboberflaeche (Fremdprojekt, FRITZ!OS 8.25) -------------
LANDEVICE_ENDPOINT = "landevice/landevice/{uid}"

# --- ANGENOMMENE Feldnamen des alten Formulars (``data.lua``, nur Rueckfall) ---
READ_PATH = ("data", "vars", "dev", "ipv4")
READ_FLAG_KEY = "static_dhcp"  # "1"/"on"/true, wenn die feste Zuweisung aktiv ist
READ_IP_KEYS = ("current", "ip")
WRITE_FLAG_FIELD = "static_dhcp"  # Formularfeld, Wert "on"

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
    """Liest (feste Zuweisung aktiv?, Adresse) aus ``edit_device``; wirft bei fremdem Aufbau.

    Nur noch Rueckfall fuer den alten ``data.lua``-Weg.
    """
    node: Any = payload
    for key in READ_PATH:
        node = node.get(key) if isinstance(node, dict) else None
    if not isinstance(node, dict) or READ_FLAG_KEY not in node:
        raise StaticIpError(
            "Die Einstellung 'immer die gleiche IPv4-Adresse' ist in der Antwort der "
            "Weboberfläche nicht zu finden (FRITZ!OS anders aufgebaut als angenommen)"
        )
    ip = next((str(node[k]).strip() for k in READ_IP_KEYS if node.get(k)), "")
    return {"fixed": _truthy(node[READ_FLAG_KEY]), "ip": ip}


def _lookup(session: Any, base: str, sid: str, mac: str) -> tuple[dict[str, str], dict[str, Any] | None]:
    """Findet das Geraet (UID, Name, IP) und - falls die Liste es hergibt - seinen Zustand.

    Zuerst ``query.lua``; fehlt dort das Geraet, die Geraeteliste ``netDev`` von
    ``data.lua``. Wirft ``ValueError``, wenn das Geraet nirgends zu finden ist.
    """
    key = plain_mac(mac)
    try:
        entries = parse_landevice_list(query_lua(session, base, sid, LANDEVICE_QUERY))
    except ValueError:
        entries = []
    for entry in entries:
        if entry["mac"] == key and entry["uid"]:
            device = {"uid": entry["uid"], "name": entry["name"], "mac": key, "ip": entry["ip"]}
            state = None
            if entry["static"] is not None:
                state = {"fixed": entry["static"], "ip": entry["ip"]}
            return device, state
    return _find_device(session, base, sid, mac), None


def _read_state(session: Any, base: str, sid: str, device: dict[str, str]) -> dict[str, Any] | None:
    """Aktueller Zustand (``fixed``, ``ip``) - ``None``, wenn die Box ihn nirgends hergibt."""
    key = plain_mac(device.get("mac"))
    try:
        for entry in parse_landevice_list(query_lua(session, base, sid, LANDEVICE_QUERY)):
            if entry["mac"] == key and entry["static"] is not None:
                return {"fixed": entry["static"], "ip": entry["ip"]}
    except ValueError:
        pass
    try:
        data = api_request(
            session, base, sid, "GET", LANDEVICE_ENDPOINT.format(uid=device["uid"])
        )
    except (DnsSettingsError, OSError):
        data = None
    if isinstance(data, dict):
        node = data.get("landevice") if isinstance(data.get("landevice"), dict) else data
        if "static_dhcp" in node:
            return {
                "fixed": _truthy(node["static_dhcp"]),
                "ip": str(node.get("ip") or "").strip(),
            }
    try:
        return parse_static_state(data_lua(session, base, sid, "edit_device", dev=device["uid"]))
    except (StaticIpError, ValueError, OSError):
        return None


def _write_rest(
    session: Any, base: str, sid: str, device: dict[str, str], fixed: bool, ip: str | None
) -> None:
    body: dict[str, str] = {"static_dhcp": "1" if fixed else "0"}
    if fixed and ip:
        body["ip"] = ip
    api_request(session, base, sid, "PUT", LANDEVICE_ENDPOINT.format(uid=device["uid"]), body)


def _write_legacy(
    session: Any,
    base: str,
    sid: str,
    device: dict[str, str],
    fixed: bool,
    ip: str | None,
    profile: str | None,
) -> None:
    """Rueckfall: Formular-POST an ``data.lua`` (Feldnamen angenommen, ungeprueft)."""
    form = {
        "sid": sid,
        "dev": device["uid"],
        "dev_name": device["name"],
        "page": "edit_device",
        "back_to_page": "netDev",
        "apply": "true",
    }
    if fixed and ip:
        form[WRITE_FLAG_FIELD] = "on"
        for index, octet in enumerate(str(ip).split(".")):
            form[f"dev_ip{index}"] = octet
    if profile:
        form["kisi_profile"] = profile
    response = session.post(f"{base}/data.lua", data=form, timeout=TIMEOUT)
    if not response.ok:
        raise StaticIpError(f"data.lua (edit_device): HTTP {response.status_code}")


def _profile_of(session: Any, base: str, sid: str, device: dict[str, str]) -> str | None:
    try:
        return parse_device_profile(data_lua(session, base, sid, "edit_device", dev=device["uid"]))
    except (ValueError, OSError):
        return None


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

    ``dry_run`` liest nur und meldet, was geschrieben wuerde. Rueckgabe:
    ``before``, ``after`` (Zustaende oder ``None``), ``device``, ``channel``
    (``"rest"`` oder ``"data.lua"``), ``verified`` und ``warnings``.
    """
    sid = login(session, base, user, password)
    try:
        device, listed = _lookup(session, base, sid, mac)
        before = listed if listed is not None else _read_state(session, base, sid, device)
        if dry_run:
            return {"before": before, "device": device["name"]}

        channel = "rest"
        profile: str | None = None
        try:
            _write_rest(session, base, sid, device, True, ip)
        except (ConfirmationRequired, SessionExpired) as err:
            raise StaticIpError(str(err)) from err
        except DnsSettingsError as err:
            if not _is_http_error(err):
                raise StaticIpError(str(err)) from err
            # Aeltere FRITZ!OS-Staende kennen die REST-Route nicht: alter Weg.
            channel = "data.lua"
            profile = _profile_of(session, base, sid, device)
            _write_legacy(session, base, sid, device, True, ip, profile)

        after = _read_state(session, base, sid, device)
        result: dict[str, Any] = {
            "before": before,
            "after": after,
            "device": device["name"],
            "channel": channel,
            "verified": False,
            "warnings": [],
        }
        if after is None:
            result["warnings"].append(
                "Die Weboberfläche liefert die feste Zuweisung nicht zum Nachlesen - "
                "das Ergebnis konnte nicht geprüft werden. Bitte in der FRITZ!Box unter "
                "Heimnetz → Netzwerk kontrollieren."
            )
            return result
        if not after["fixed"]:
            restored = _restore(session, base, sid, device, before, channel, profile)
            raise StaticIpError(
                "Die FRITZ!Box hat die feste Adresse nicht übernommen (Zuweisung nach dem "
                f"Schreiben: aus; Weg: {channel}). Hat das Benutzerkonto der Integration die "
                "Zusatzbestätigung (Zwei-Faktor) aktiv, verwirft die Box Änderungen ohne "
                "Meldung - dann ein Konto ohne Zusatzbestätigung verwenden. "
                + (
                    "Ausgangszustand wiederhergestellt."
                    if restored
                    else "Ausgangszustand konnte nicht bestätigt werden - bitte in der Box prüfen."
                    if before and before.get("fixed")
                    else "Es wurde nichts geändert."
                )
            )
        result["verified"] = True
        if after["ip"] and after["ip"] != ip:
            result["warnings"].append(
                f"Die FRITZ!Box meldet derzeit noch {after['ip']}; die Adresse {ip} wird erst "
                "nach einer Neuverbindung des Geräts sichtbar. Falls sie danach nicht erscheint, "
                "hat die Box das Adressfeld nicht übernommen - dann in der Box nachtragen."
            )
        return result
    finally:
        logout(session, base, sid)


def _restore(
    session: Any,
    base: str,
    sid: str,
    device: dict[str, str],
    before: dict[str, Any] | None,
    channel: str,
    profile: str | None,
) -> bool:
    """Stellt eine vorher aktive feste Zuweisung wieder her (``False``, wenn unklar)."""
    if not before or not before.get("fixed"):
        return False
    try:
        if channel == "rest":
            _write_rest(session, base, sid, device, True, before.get("ip") or None)
        else:
            _write_legacy(session, base, sid, device, True, before.get("ip") or None, profile)
        now = _read_state(session, base, sid, device)
    except (DnsSettingsError, StaticIpError, ValueError, OSError):
        return False
    return bool(now and now.get("fixed"))
