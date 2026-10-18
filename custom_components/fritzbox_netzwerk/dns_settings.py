# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 362573f1d57c0c9be046c3afd85bceeee65d93d00772f56138a8b6dfbd5e2e14
"""DNS-Einstellungen der FRITZ!Box ueber die REST-Schnittstelle der Weboberflaeche.

EXPERIMENTELL: Das ist NICHT TR-064. Die neue Weboberflaeche (FRITZ!OS 8,
ermittelt an einer FRITZ!Box 5690 Pro) liest und schreibt ihre Einstellungen ueber
``/api/v0/generic/<name>`` mit dem Kopf ``AUTHORIZATION: AVM-SID <sid>`` und
JSON-Koerper. AVM dokumentiert diese Schnittstelle nicht; sie kann sich mit jeder
FRITZ!OS-Version aendern.

Belegt (am Quelltext der Oberflaeche und an den echten GET-Antworten dieser Box
gelesen):
- ``GET /api/v0/generic/dnscfg`` liefert u. a. ``ipv4_use_user_dns``,
  ``ipv4_user_firstdns``, ``ipv4_user_seconddns``, ``ipv6_use_user_dns``,
  ``ipv6_user_firstdns``, ``ipv6_user_seconddns``, ``ipv4_dhcpserver_lan_dns``
  (Zeichenketten, "0"/"1" fuer Schalter, "0.0.0.0" bzw. "::" fuer "leer").
- ``GET /api/v0/generic/ipv6`` liefert u. a. ``lan_dns6_server`` und
  ``radv_advdns`` ("DNSv6-Server auch ueber Router Advertisement bekanntgeben").
- Die Oberflaeche schreibt per ``PUT`` auf denselben Pfad mit dem GANZEN Objekt;
  bei kritischen Aenderungen antwortet die Box mit dem Fehlercode ``TWO-FACTOR``
  (Bestaetigung noetig), bei abgelaufener Sitzung mit ``INVALID-SID``.

NICHT geprueft (an keiner Box ausgefuehrt): ob ein ``PUT`` von Dritten mit dem
Kopf ``Client-Name`` dieser Integration akzeptiert wird, welcher HTTP-Status bei
``TWO-FACTOR`` kommt, wie die Bestaetigung abgeschlossen wird und ob ``PUT`` auf
``ipv6`` nur die gewuenschten Felder aendert. Deshalb gilt beim Schreiben:
vorher lesen, nur die gewuenschten Felder aendern, danach erneut lesen und bei
Abweichung den Ausgangszustand zurueckschreiben.

Seit 1.9.1 (Issue #30, gemeldet an einer FRITZ!Box 6591 Cable, FRITZ!OS 8.25):
Dort antwortet ``PUT ipv6`` mit HTTP 400, obwohl die Box den Wert uebernimmt.
Ein HTTP-Fehler auf ``ipv6`` gilt deshalb nicht sofort als Misserfolg: der Zustand
wird nachgelesen, und stimmt er mit dem Wunsch ueberein, zaehlt die Aenderung als
geschrieben (mit Hinweis im Ergebnis). Sonst bleibt es beim Fehler und der
Ausgangszustand wird zurueckgeschrieben. Der Ablauf ist an keiner Box geprueft;
belegt ist er nur durch die Meldung im Issue.

Das Modul enthaelt keine Home-Assistant- und keine fritzconnection-Importe und
ist mit Attrappen pruefbar.
"""
from __future__ import annotations

import copy
import ipaddress
import json
from typing import Any

from .webui import login, logout

API_PREFIX = "api/v0/generic/"
DNSCFG = "dnscfg"
IPV6 = "ipv6"
CLIENT_NAME = "fritzbox_netzwerk"
TIMEOUT = 10

EMPTY_V4 = "0.0.0.0"
EMPTY_V6 = "::"


class DnsSettingsError(ValueError):
    """Allgemeiner Fehler beim Lesen oder Aendern der DNS-Einstellungen."""


class ConfirmationRequired(DnsSettingsError):
    """Die Box verlangt eine Bestaetigung (``TWO-FACTOR``) - nichts wurde geaendert."""


class SessionExpired(DnsSettingsError):
    """Die Sitzung wurde von der Box abgelehnt (``INVALID-SID``)."""


# Dienstfeld -> (Endpunkt, Feld der Box, Typ). Nur diese Felder duerfen geschrieben werden.
FIELD_MAP: dict[str, tuple[str, str, str]] = {
    "internet_ipv4_custom": (DNSCFG, "ipv4_use_user_dns", "bool"),
    "internet_ipv4_dns1": (DNSCFG, "ipv4_user_firstdns", "v4_optional"),
    "internet_ipv4_dns2": (DNSCFG, "ipv4_user_seconddns", "v4_optional"),
    "internet_ipv6_custom": (DNSCFG, "ipv6_use_user_dns", "bool"),
    "internet_ipv6_dns1": (DNSCFG, "ipv6_user_firstdns", "v6_optional"),
    "internet_ipv6_dns2": (DNSCFG, "ipv6_user_seconddns", "v6_optional"),
    "home_ipv4_dns": (DNSCFG, "ipv4_dhcpserver_lan_dns", "v4_required"),
    "home_ipv6_dns": (IPV6, "lan_dns6_server", "v6_required"),
    "home_ipv6_advertise": (IPV6, "radv_advdns", "bool"),
}

CHANGE_FIELDS = tuple(FIELD_MAP)

# Felder, die vorhanden sein muessen, bevor irgendetwas geschrieben wird.
REQUIRED_KEYS: dict[str, tuple[str, ...]] = {
    DNSCFG: (
        "ipv4_use_user_dns",
        "ipv4_user_firstdns",
        "ipv4_user_seconddns",
        "ipv6_use_user_dns",
        "ipv6_user_firstdns",
        "ipv6_user_seconddns",
        "ipv4_dhcpserver_lan_dns",
    ),
    IPV6: ("lan_dns6_server", "radv_advdns"),
}


def validate_address(value: Any, version: int, field: str) -> str:
    """Prueft eine DNS-Server-Adresse und liefert die normalisierte Schreibweise.

    Abgelehnt werden: keine Adresse, falsche IP-Version, unspezifiziert (0.0.0.0, ::),
    Loopback, Multicast, reservierte und Link-Local-Adressen (bei IPv6 fehlt die
    Zonenangabe) sowie der IPv4-Broadcast.
    """
    text = str(value if value is not None else "").strip()
    try:
        address = ipaddress.ip_address(text)
    except ValueError as err:
        raise DnsSettingsError(f"{field}: '{text}' ist keine gültige IPv{version}-Adresse") from err
    if address.version != version:
        raise DnsSettingsError(f"{field}: '{text}' ist keine IPv{version}-Adresse")
    if (
        address.is_unspecified
        or address.is_loopback
        or address.is_multicast
        or address.is_reserved
        or address.is_link_local
        or (version == 4 and text == "255.255.255.255")
    ):
        raise DnsSettingsError(f"{field}: '{text}' ist als DNS-Server nicht zulässig")
    return str(address)


def _is_empty(value: Any) -> bool:
    return str(value if value is not None else "").strip() in ("", EMPTY_V4, EMPTY_V6)


def _bool_value(value: Any, field: str) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    raise DnsSettingsError(f"{field}: erwartet wird wahr oder falsch")


def _coerce(field: str, value: Any) -> str:
    """Wandelt einen Dienstwert in den Rohwert der Box um (prueft ihn dabei)."""
    _endpoint, _key, kind = FIELD_MAP[field]
    if kind == "bool":
        return _bool_value(value, field)
    version = 4 if kind.startswith("v4") else 6
    empty = EMPTY_V4 if version == 4 else EMPTY_V6
    if kind.endswith("optional") and str(value if value is not None else "").strip() == "":
        return empty
    return validate_address(value, version, field)


def plan_changes(
    current: dict[str, dict[str, Any]], changes: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]]]:
    """Berechnet die neuen Objekte und die Unterschiede - schreibt nichts.

    ``current`` ist ``{"dnscfg": {...}, "ipv6": {...}}`` (nur die gebrauchten
    Endpunkte muessen vorhanden sein). Rueckgabe: neue Objekte (Kopien, nur
    geaenderte Endpunkte) und ``{Dienstfeld: {"vorher": ..., "nachher": ...}}``.
    Wirft ``DnsSettingsError`` bei unbekannten Feldern, ungueltigen Werten oder
    einem unzulaessigen Gesamtergebnis (eigene Server an, aber kein erster Server).
    """
    unknown = sorted(set(changes) - set(FIELD_MAP))
    if unknown:
        raise DnsSettingsError(f"Unbekannte Felder: {', '.join(unknown)}")
    wanted = {field: value for field, value in changes.items() if value is not None}
    if not wanted:
        raise DnsSettingsError("Es wurde keine Änderung angegeben")

    new: dict[str, dict[str, Any]] = {}
    diff: dict[str, dict[str, str]] = {}
    for field, value in wanted.items():
        endpoint, key, _kind = FIELD_MAP[field]
        raw = current.get(endpoint)
        if not isinstance(raw, dict):
            raise DnsSettingsError(f"Die Einstellungen '{endpoint}' sind nicht lesbar")
        missing = [name for name in REQUIRED_KEYS[endpoint] if name not in raw]
        if missing:
            raise DnsSettingsError(
                f"'{endpoint}' enthält nicht die erwarteten Felder ({', '.join(missing)}) - "
                "FRITZ!OS geändert? Es wird nichts geschrieben."
            )
        coerced = _coerce(field, value)
        before = str(raw.get(key))
        if before == coerced:
            continue
        target = new.setdefault(endpoint, copy.deepcopy(raw))
        target[key] = coerced
        diff[field] = {"vorher": before, "nachher": coerced}

    cfg = new.get(DNSCFG) or current.get(DNSCFG) or {}
    for prefix, label, empty in (("ipv4", "IPv4", EMPTY_V4), ("ipv6", "IPv6", EMPTY_V6)):
        if cfg.get(f"{prefix}_use_user_dns") == "1" and _is_empty(cfg.get(f"{prefix}_user_firstdns")):
            raise DnsSettingsError(
                f"Eigene {label}-DNS-Server sind eingeschaltet, aber es ist kein erster Server eingetragen"
            )
    return new, diff


def api_request(
    session: Any, base: str, sid: str, method: str, endpoint: str, body: Any = None
) -> Any:
    """Eine Anfrage an ``/api/v0/generic/<endpoint>`` (``DnsSettingsError`` bei Fehlern)."""
    response = session.request(
        method,
        f"{base}/{API_PREFIX}{endpoint}",
        headers={
            "AUTHORIZATION": f"AVM-SID {sid}",
            "Content-Type": "application/json",
            "Client-Name": CLIENT_NAME,
        },
        data=json.dumps(body) if body is not None else None,
        timeout=TIMEOUT,
    )
    text = response.text or ""
    try:
        data: Any = response.json()
    except ValueError:
        data = None
    suspicious = (not response.ok) or (isinstance(data, dict) and "errors" in data)
    if suspicious:
        marker = text.upper()
        if "TWO-FACTOR" in marker:
            raise ConfirmationRequired(
                "Die FRITZ!Box verlangt eine Bestätigung der Änderung (Zwei-Faktor). "
                "Es wurde nichts geändert - bestätige die Anfrage an der Box und wiederhole sie."
            )
        if "INVALID-SID" in marker:
            raise SessionExpired("Die FRITZ!Box hat die Sitzung abgelehnt (INVALID-SID)")
    if not response.ok:
        raise DnsSettingsError(f"{method} {endpoint}: HTTP {response.status_code}")
    if not isinstance(data, dict):
        if method != "GET":
            # Welche Antwort ein erfolgreiches PUT liefert, ist ungeprueft; der
            # Zustand wird danach ohnehin per GET nachgelesen und verglichen.
            return {}
        raise DnsSettingsError(f"{method} {endpoint}: keine JSON-Antwort")
    return data


def _shown(value: Any) -> str:
    return "" if _is_empty(value) else str(value)


def summarize_dns(
    dnscfg: dict[str, Any], ipv6: dict[str, Any] | None
) -> dict[str, Any]:
    """Fasst die Rohwerte uebersichtlich zusammen (ohne etwas zu deuten, was unklar ist)."""
    result: dict[str, Any] = {
        "internet": {
            "ipv4": {
                "eigene_server": dnscfg.get("ipv4_use_user_dns") == "1",
                "dns1": _shown(dnscfg.get("ipv4_user_firstdns")),
                "dns2": _shown(dnscfg.get("ipv4_user_seconddns")),
            },
            "ipv6": {
                "eigene_server": dnscfg.get("ipv6_use_user_dns") == "1",
                "dns1": _shown(dnscfg.get("ipv6_user_firstdns")),
                "dns2": _shown(dnscfg.get("ipv6_user_seconddns")),
            },
        },
        "heimnetz": {
            "ipv4_lokaler_dns": _shown(dnscfg.get("ipv4_dhcpserver_lan_dns")),
            "ipv6_lokaler_dns": _shown(ipv6.get("lan_dns6_server")) if ipv6 else None,
            "ipv6_per_router_advertisement": (ipv6.get("radv_advdns") == "1") if ipv6 else None,
        },
        "weitere": {
            "dns_over_tls": dnscfg.get("dns_over_tls_enabled") == "1",
            "oeffentlicher_fallback": dnscfg.get("public_dns_servers_use_as_fallback") == "1",
            "wpad_schutz": dnscfg.get("wpad_protection") == "1",
        },
        "rohwerte_dnscfg": {key: str(value) for key, value in dnscfg.items()},
    }
    return result


def _read_all(
    session: Any, base: str, sid: str, need_ipv6: bool
) -> tuple[dict[str, Any], dict[str, Any] | None, str | None]:
    dnscfg = api_request(session, base, sid, "GET", DNSCFG)
    ipv6: dict[str, Any] | None = None
    ipv6_error: str | None = None
    try:
        ipv6 = api_request(session, base, sid, "GET", IPV6)
    except DnsSettingsError as err:
        if need_ipv6 or isinstance(err, (ConfirmationRequired, SessionExpired)):
            raise
        ipv6_error = str(err)
    return dnscfg, ipv6, ipv6_error


def read_dns_settings(session: Any, base: str, user: str, password: str) -> dict[str, Any]:
    """Meldet sich an und liest alle DNS-Einstellungen (nur lesend)."""
    sid = login(session, base, user, password)
    try:
        dnscfg, ipv6, ipv6_error = _read_all(session, base, sid, need_ipv6=False)
    finally:
        logout(session, base, sid)
    result = summarize_dns(dnscfg, ipv6)
    if ipv6_error:
        result["hinweis"] = f"IPv6-Heimnetz nicht lesbar: {ipv6_error}"
    return result


def change_dns_settings(
    session: Any,
    base: str,
    user: str,
    password: str,
    changes: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Aendert DNS-Einstellungen: lesen, nur Gewuenschtes aendern, schreiben, nachpruefen.

    Mit ``dry_run`` wird nur berechnet, was geaendert wuerde (``geschrieben: False``).
    Weicht der Zustand nach dem Schreiben vom Soll ab, wird der Ausgangszustand
    zurueckgeschrieben und ein Fehler geworfen (der Text nennt den Ausgang).
    """
    endpoints = {FIELD_MAP[f][0] for f, v in changes.items() if f in FIELD_MAP and v is not None}
    sid = login(session, base, user, password)
    written: list[str] = []
    originals: dict[str, dict[str, Any]] = {}
    try:
        dnscfg, ipv6, _err = _read_all(session, base, sid, need_ipv6=IPV6 in endpoints)
        current: dict[str, dict[str, Any]] = {DNSCFG: dnscfg}
        if ipv6 is not None:
            current[IPV6] = ipv6
        originals = copy.deepcopy(current)
        new, diff = plan_changes(current, changes)
        if dry_run or not diff:
            return {
                "geschrieben": False,
                "vorschau": dry_run,
                "aenderungen": diff,
                "hinweis": None if diff else "Alle Werte entsprechen bereits dem Wunsch",
            }
        notes: list[str] = []
        try:
            for endpoint in (DNSCFG, IPV6):
                if endpoint in new:
                    try:
                        api_request(session, base, sid, "PUT", endpoint, new[endpoint])
                    except (ConfirmationRequired, SessionExpired):
                        raise
                    except DnsSettingsError as err:
                        # Issue #30: manche Boxen melden HTTP 400 und uebernehmen
                        # den IPv6-Wert trotzdem - dann nachlesen und vergleichen.
                        if endpoint != IPV6 or not _is_http_error(err):
                            raise
                        if not _ipv6_applied(session, base, sid, new[IPV6], diff):
                            raise
                        notes.append(
                            f"Die FRITZ!Box antwortete auf das Schreiben der IPv6-Einstellung mit "
                            f"einem Fehler ({err}), hat den Wert aber übernommen."
                        )
                    written.append(endpoint)
            after, after_ipv6, _e = _read_all(session, base, sid, need_ipv6=IPV6 in new)
            check = {DNSCFG: after, IPV6: after_ipv6 or {}}
            for endpoint, expected in new.items():
                for field, (ep, key, _k) in FIELD_MAP.items():
                    if ep == endpoint and field in diff and str(check[endpoint].get(key)) != expected[key]:
                        raise DnsSettingsError(
                            f"Die FRITZ!Box hat '{key}' nicht übernommen "
                            f"(ist: {check[endpoint].get(key)}, erwartet: {expected[key]})"
                        )
        except ConfirmationRequired:
            # Schon Geschriebenes zuruecknehmen, damit nie nur die Haelfte gilt.
            if written:
                _rollback(session, base, sid, written, originals)
            raise
        except DnsSettingsError as err:
            restored = _rollback(session, base, sid, written, originals)
            raise DnsSettingsError(
                f"{err}. Ausgangszustand {'wiederhergestellt' if restored else 'NICHT sicher wiederhergestellt - bitte in der FRITZ!Box prüfen'}; "
                f"vorher: {json.dumps({f: d['vorher'] for f, d in diff.items()}, ensure_ascii=False)}"
            ) from err
        summary = summarize_dns(after, after_ipv6)
        result: dict[str, Any] = {
            "geschrieben": True,
            "vorschau": False,
            "aenderungen": diff,
            "ergebnis": summary,
        }
        if notes:
            result["hinweis"] = " ".join(notes)
        return result
    finally:
        logout(session, base, sid)


def _is_http_error(err: Exception) -> bool:
    """Ob ``api_request`` wegen eines HTTP-Status (nicht wegen fehlerhafter Antwort) scheiterte."""
    return ": HTTP " in str(err)


def _ipv6_applied(
    session: Any,
    base: str,
    sid: str,
    expected: dict[str, Any],
    diff: dict[str, dict[str, str]],
) -> bool:
    """Ob die gewuenschten ``ipv6``-Felder nach einem Fehler beim Schreiben schon gelten."""
    try:
        _dnscfg, ipv6, _err = _read_all(session, base, sid, need_ipv6=True)
    except (DnsSettingsError, OSError):
        return False
    if not isinstance(ipv6, dict):
        return False
    keys = [key for field, (ep, key, _k) in FIELD_MAP.items() if ep == IPV6 and field in diff]
    return bool(keys) and all(str(ipv6.get(key)) == str(expected.get(key)) for key in keys)


def _rollback(
    session: Any, base: str, sid: str, written: list[str], originals: dict[str, dict[str, Any]]
) -> bool:
    """Schreibt die vorher gelesenen Objekte zurueck (Best Effort). ``True`` = alles gelungen."""
    ok = True
    for endpoint in reversed(written):
        try:
            api_request(session, base, sid, "PUT", endpoint, originals[endpoint])
        except (DnsSettingsError, OSError):
            ok = False
    return ok
