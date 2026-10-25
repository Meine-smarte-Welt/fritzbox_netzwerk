# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): fa15ccd1042bc9d0e2b30dfd3ff11209c0460cfd3382d5c1d63580263fbc43d1
"""Inoffizieller Zugriff auf die FRITZ!Box-Weboberfläche (nur lesend).

ACHTUNG - EXPERIMENTELL: Dieses Modul spricht NICHT TR-064, sondern die
Weboberfläche der Box (``login_sid.lua`` und ``data.lua``). Beides ist von AVM
nicht für Dritte dokumentiert und kann sich mit jeder FRITZ!OS-Version ändern.
Der Anmeldeablauf (``login_sid.lua``) ist von AVM beschrieben; die Auswertung
der Seite ``ecoStat`` beruht auf Beobachtungen aus der Community und ist an
einer echten Box NICHT geprüft. Deshalb ist die Funktion standardmäßig aus und
jeder Fehler führt nur dazu, dass die Werte fehlen.

Das Modul enthält weder Home-Assistant- noch fritzconnection-Importe und ist
mit Attrappen prüfbar.
"""
from __future__ import annotations

import hashlib
import html
import json
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urlsplit

EMPTY_SID = "0000000000000000"
TIMEOUT = 10
# Lesezeit fuer die schweren Seiten der Weboberflaeche (``netDev`` mit allen
# Geraeten, ``edit_device``, ``kidPro``): Boxen mit vielen Geraeten brauchen dafuer
# laenger als 10 s (Rueckmeldung zu 2.0.0: "Read timed out (read timeout=10)").
SLOW_TIMEOUT = 40


def base_url(address: str, port: int | None, remote: bool) -> str:
    """Adresse der Weboberfläche (nicht die TR-064-Adresse).

    Lokal: Standardport der Oberfläche (80/443) - der TR-064-Port (49000/49443)
    gehört nicht dazu. Fernzugriff: HTTPS auf dem konfigurierten Port, ohne den
    TR-064-Präfix ``/tr064``.
    """
    parsed = urlsplit(address if "//" in address else f"//{address}")
    host = parsed.hostname or address
    authority = f"[{host}]" if ":" in host else host
    if remote:
        return f"https://{authority}:{port or 443}"
    scheme = parsed.scheme if parsed.scheme in ("http", "https") else "http"
    return f"{scheme}://{authority}"


def solve_challenge(challenge: str, password: str) -> str:
    """Berechnet die Antwort auf eine ``login_sid.lua``-Challenge.

    Neues Verfahren (FRITZ!OS 7.24+): ``2$iter1$salt1$iter2$salt2`` mit zwei
    PBKDF2-Runden. Altes Verfahren: MD5 über ``challenge-password`` in UTF-16LE
    (Zeichen über U+00FF werden dort durch ``.`` ersetzt).
    """
    if challenge.startswith("2$"):
        try:
            _, iter1, salt1, iter2, salt2 = challenge.split("$")
            hash1 = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), bytes.fromhex(salt1), int(iter1)
            )
            hash2 = hashlib.pbkdf2_hmac("sha256", hash1, bytes.fromhex(salt2), int(iter2))
        except (ValueError, TypeError) as err:
            raise ValueError("Unbekanntes Challenge-Format") from err
        return f"{salt2}${hash2.hex()}"
    cleaned = "".join(ch if ord(ch) <= 255 else "." for ch in password)
    digest = hashlib.md5(f"{challenge}-{cleaned}".encode("utf-16le")).hexdigest()
    return f"{challenge}-{digest}"


def parse_session_info(text: str) -> dict[str, str]:
    """Liest ``SID``, ``Challenge`` und ``BlockTime`` aus der SessionInfo-XML."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as err:
        raise ValueError("Ungültige SessionInfo") from err
    return {tag: (root.findtext(tag) or "").strip() for tag in ("SID", "Challenge", "BlockTime")}


def login(session: Any, base: str, user: str, password: str) -> str:
    """Meldet sich an und liefert die Session-ID (``ValueError`` bei Fehlschlag)."""
    first = session.get(f"{base}/login_sid.lua", params={"version": "2"}, timeout=TIMEOUT)
    if not first.ok:
        raise ValueError(f"login_sid.lua: HTTP {first.status_code}")
    info = parse_session_info(first.text)
    if info["SID"] and info["SID"] != EMPTY_SID:
        return info["SID"]
    if info["BlockTime"] not in ("", "0"):
        raise ValueError(f"Anmeldung gesperrt für {info['BlockTime']} s")
    if not info["Challenge"]:
        raise ValueError("Keine Challenge erhalten")
    answer = solve_challenge(info["Challenge"], password)
    second = session.post(
        f"{base}/login_sid.lua",
        params={"version": "2"},
        data={"username": user, "response": answer},
        timeout=TIMEOUT,
    )
    if not second.ok:
        raise ValueError(f"login_sid.lua: HTTP {second.status_code}")
    sid = parse_session_info(second.text)["SID"]
    if not sid or sid == EMPTY_SID:
        raise ValueError("Anmeldung an der Weboberfläche abgelehnt")
    return sid


def _last_number(series: Any) -> float | None:
    """Letzter numerische Wert einer Zeitreihe (``None``, wenn keiner vorhanden)."""
    if not isinstance(series, (list, tuple)):
        return None
    for value in reversed(series):
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str) and re.fullmatch(r"-?\d+(\.\d+)?", value.strip()):
            return float(value)
    return None


def parse_eco_stat(payload: Any) -> dict[str, float | None]:
    """Wertet die JSON-Antwort von ``data.lua`` (Seite ``ecoStat``) tolerant aus.

    ANNAHMEN (an keiner echten Box geprüft):
    - ``data.cpuutil.series[0]`` ist der Verlauf der CPU-Auslastung in Prozent,
      der letzte Wert ist der jüngste.
    - ``data.ramusage.series`` hat bei drei Reihen die Anteile (belegt, Cache,
      frei) in Prozent; die Auslastung ist dann 100 minus der letzten Reihe.
    - ``data.cputemp.series[0]`` ist die Temperatur in °C.
    Fehlt etwas oder passt die Form nicht, bleibt der Wert ``None``.
    """
    result: dict[str, float | None] = {"cpu": None, "ram": None, "temperature": None}
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return result

    def series_of(name: str) -> list[Any]:
        block = data.get(name)
        series = block.get("series") if isinstance(block, dict) else None
        return series if isinstance(series, list) else []

    cpu = series_of("cpuutil")
    if cpu:
        result["cpu"] = _last_number(cpu[0])
    temp = series_of("cputemp")
    if temp:
        result["temperature"] = _last_number(temp[0])
    ram = series_of("ramusage")
    if len(ram) >= 3:
        free = _last_number(ram[-1])
        if free is not None and 0 <= free <= 100:
            result["ram"] = round(100.0 - free, 1)
    for key in ("cpu",):
        value = result[key]
        if value is not None and not 0 <= value <= 100:
            result[key] = None
    return result


def logout(session: Any, base: str, sid: str) -> None:
    """Meldet die Sitzung ab (best effort - die Box räumt sie sonst selbst auf)."""
    try:
        session.get(f"{base}/home/home.lua", params={"sid": sid, "logout": "1"}, timeout=TIMEOUT)
    except Exception:  # noqa: BLE001 - Abmelden darf nie ein Ergebnis kippen
        pass


def data_lua(
    session: Any,
    base: str,
    sid: str,
    page: str,
    request_timeout: float = TIMEOUT,
    **fields: str,
) -> Any:
    """Ruft ``data.lua`` auf und liefert die Antwort (JSON-Objekt, sonst Text)."""
    form = {"xhr": "1", "sid": sid, "lang": "de", "page": page, "no_sidrenew": ""}
    form.update(fields)
    response = session.post(f"{base}/data.lua", data=form, timeout=request_timeout)
    if not response.ok:
        raise ValueError(f"data.lua ({page}): HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError:
        return response.text


def fetch_system_stats(session: Any, base: str, user: str, password: str) -> dict[str, float | None]:
    """Meldet sich an, ruft ``ecoStat`` ab und liefert CPU/RAM/Temperatur.

    Wirft bei jedem Fehler ``ValueError`` oder die Netzwerkfehler des
    übergebenen ``requests``-ähnlichen Objekts; der Aufrufer fängt sie ab.
    """
    sid = login(session, base, user, password)
    try:
        payload = data_lua(session, base, sid, "ecoStat")
    finally:
        logout(session, base, sid)
    if not isinstance(payload, dict):
        raise ValueError("data.lua lieferte kein JSON")
    return parse_eco_stat(payload)


# ---------------------------------------------------------------------------
# Kindersicherung: Zugangsprofile (EXPERIMENTELL)
#
# Quelle der Anfragen: frei einsehbare Community-Skripte (FritzBoxShell von
# jhubig - ``SETPROFILE``/``LISTDEVICES``, FHEM-Forum, ioBroker-Forum). Weder
# TR-064 noch AVM dokumentieren das; die Formularfelder können sich mit
# FRITZ!OS ändern. Deshalb: Option standardmäßig aus, Nachkontrolle nach dem
# Schreiben und klare Fehlermeldungen statt Raten.
# ---------------------------------------------------------------------------

PROFILE_ID_RE = re.compile(r"filtprof\d+")
_TAG_RE = re.compile(r"<[^>]*\bvalue=[\"'](filtprof\d+)[\"'][^>]*>", re.IGNORECASE)
_NAME_RE = re.compile(r"\bdata-(?:profile-?)?name=[\"']([^\"']*)[\"']", re.IGNORECASE)
_OPTION_RE = re.compile(
    r"<option\b[^>]*\bvalue=[\"'](filtprof\d+)[\"'][^>]*>(.*?)</option>", re.IGNORECASE | re.DOTALL
)
_ROW_RE = re.compile(r"<(tr|li)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_CELL_RE = re.compile(r"<(t[dh])\b([^>]*)>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
_NAME_CELL_RE = re.compile(r"(?:datalabel|data-label|class)=[\"'][^\"']*name", re.IGNORECASE)
_ID_KEYS = ("id", "value", "uid", "UID", "key", "profile", "profile_id", "profileId")
_NAME_KEYS = (
    "name", "Name", "text", "label", "title", "displayName", "display_name", "profile_name", "caption",
)
# Beschriftungen von Schaltflächen und Spaltenköpfen, die nie ein Profilname sind.
_NOT_NAMES = frozenset(
    {"bearbeiten", "löschen", "loeschen", "ändern", "edit", "delete", "remove", "name", "profil", "profile"}
)
# REST-Pfad der Profilliste (FRITZ!OS 8.x, so lädt ihn die Oberfläche selbst). Dort stehen die
# Standardprofile mit LEEREM ``name`` - die Oberfläche blendet ihre Namen selbst ein.
FILTER_PROFILE_PATH = "api/v0/generic/filter_profile"
# Namen der drei fest eingebauten Profile, wie die Oberfläche (FRITZ!OS 8.40, Deutsch) sie zeigt:
# Standard, Gast, Unbeschränkt. Nur letzter Rückfall, wenn die Box keinen Namen liefert.
DEFAULT_PROFILE_NAMES = {"filtprof1": "Standard", "filtprof2": "Gast", "filtprof3": "Unbeschränkt"}
_LOGGER = logging.getLogger(__name__)
_names_warned = False


def normalize_mac(mac: Any) -> str:
    """Nur Hex-Zeichen in Großschreibung (Schlüssel zum Vergleich)."""
    return re.sub(r"[^0-9A-Fa-f]", "", str(mac or "")).upper()


def _clean_text(fragment: Any) -> str:
    """Sichtbarer Text eines HTML-Schnipsels (ohne Tags, Entitäten aufgelöst, Leerraum zusammengefasst)."""
    text = re.sub(r"<[^>]*>", " ", str(fragment or ""))
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _usable_name(value: Any, profile_id: str = "") -> str:
    """Bereinigter Profilname oder ``""``, wenn der Wert die ID, eine Schaltfläche o. ä. ist."""
    if not isinstance(value, str):
        return ""
    name = _clean_text(value)
    if not name or len(name) > 80 or name == profile_id or PROFILE_ID_RE.fullmatch(name):
        return ""
    if name.casefold() in _NOT_NAMES or re.fullmatch(r"[\W_]+", name):
        return ""
    return name


def _json_profiles(node: Any, found: dict[str, str], depth: int = 0) -> None:
    """Sammelt ``ID -> Name`` aus beliebig verschachteltem JSON (Reihenfolge des ersten Fundes bleibt).

    Erkannt werden Objekte mit einem ID-Feld (``id``, ``value``, ``UID`` …) neben einem Namensfeld
    (``name``, ``text``, ``label`` …) und Zuordnungen der Form ``{"filtprof1": "Standard"}``. Das Feld
    ``selected`` zählt bewusst nicht als ID-Feld (es nennt nur die Auswahl, nicht ein Profil).
    """
    if depth > 12:
        return

    def put(profile_id: str, name: str) -> None:
        if not found.get(profile_id):
            found[profile_id] = name

    if isinstance(node, dict):
        profile_id = next(
            (v for k, v in node.items() if k in _ID_KEYS and isinstance(v, str) and PROFILE_ID_RE.fullmatch(v)),
            None,
        )
        if profile_id:
            put(profile_id, next((n for n in (_usable_name(node.get(k), profile_id) for k in _NAME_KEYS) if n), ""))
        for key, value in node.items():
            if isinstance(key, str) and PROFILE_ID_RE.fullmatch(key):
                if isinstance(value, str):
                    put(key, _usable_name(value, key))
                elif isinstance(value, dict):
                    put(key, next((n for n in (_usable_name(value.get(k), key) for k in _NAME_KEYS) if n), ""))
            _json_profiles(value, found, depth + 1)
    elif isinstance(node, list):
        for item in node:
            _json_profiles(item, found, depth + 1)


def _html_profiles(text: str) -> dict[str, str]:
    """Sammelt ``ID -> Name`` aus einer HTML-Seite (``value="filtprofN"`` markiert ein Profil).

    Namen kommen, in dieser Reihenfolge, aus dem Text eines ``<option>``, aus einem ``data-name``
    im selben Tag oder aus der Tabellen-/Listenzeile, in der die ID steht (bevorzugt die Zelle mit
    „name“ in Klasse oder ``datalabel``, sonst die erste Zelle mit brauchbarem Text).
    """
    found: dict[str, str] = {}

    def put(profile_id: str, name: str) -> None:
        if not found.get(profile_id):
            found[profile_id] = name

    for match in _OPTION_RE.finditer(text):
        put(match.group(1), _usable_name(match.group(2), match.group(1)))
    for match in _TAG_RE.finditer(text):
        data_name = _NAME_RE.search(match.group(0))
        put(match.group(1), _usable_name(data_name.group(1), match.group(1)) if data_name else "")
    for row in _ROW_RE.finditer(text):
        ids = list(dict.fromkeys(PROFILE_ID_RE.findall(row.group(0))))
        if len(ids) != 1 or ids[0] not in found or found[ids[0]]:
            continue
        cells = [(m.group(2), _clean_text(m.group(3))) for m in _CELL_RE.finditer(row.group(0))]
        ordered = [t for a, t in cells if _NAME_CELL_RE.search(a)] + [t for _, t in cells]
        put(ids[0], next((n for n in (_usable_name(t, ids[0]) for t in ordered) if n), ""))
    return found


def parse_profile_names(page: Any) -> dict[str, str]:
    """``ID -> Name`` aus einer Seite der Weboberfläche (HTML-Text oder JSON); nur gefundene Namen."""
    found: dict[str, str] = {}
    if isinstance(page, (dict, list)):
        _json_profiles(page, found)
    elif isinstance(page, str):
        found = _html_profiles(page)
    return {pid: name for pid, name in found.items() if name}


def parse_profiles(page: Any) -> list[dict[str, str]]:
    """Liest die Zugangsprofile (``id``, ``name``) aus der Seite ``kidPro`` (HTML oder JSON).

    Ein Profil ist jede ``value="filtprofNNN"``-Markierung (bei JSON: ein Objekt mit ID-Feld). Der
    Name stammt aus dem ersten Treffer von :func:`_html_profiles` bzw. :func:`_json_profiles`;
    fehlt er, bleibt ``name`` leer (der Aufrufer ergänzt ihn aus weiteren Quellen). Doppelte IDs
    zählen einmal.
    """
    if isinstance(page, (dict, list)):
        found: dict[str, str] = {}
        _json_profiles(page, found)
    else:
        found = _html_profiles(page if isinstance(page, str) else "")
    return [{"id": pid, "name": name} for pid, name in found.items()]


def _fill_names(profiles: list[dict[str, str]], names: dict[str, str]) -> None:
    """Trägt fehlende Namen aus ``names`` nach (vorhandene bleiben unverändert)."""
    for profile in profiles:
        if not profile["name"]:
            profile["name"] = names.get(profile["id"], "")


def _profile_excerpt(page: Any) -> str:
    """Kurzer Auszug (ohne Session-ID) rund um das erste Profil einer Seite - für die Fehlersuche."""
    text = json.dumps(page, ensure_ascii=False) if isinstance(page, (dict, list)) else str(page or "")
    start = text.find("filtprof")
    if start < 0:
        return text[:300]
    excerpt = re.sub(r"\s+", " ", text[max(0, start - 250) : start + 450])
    return re.sub(r"\bsid=[0-9a-fA-F]{8,}", "sid=…", excerpt)


def _profile_id_number(profile: dict[str, str]) -> int:
    """Zahl hinter ``filtprof`` (für die Reihenfolge wie in der Oberfläche: 1, 2, 3, 1008 …)."""
    digits = re.sub(r"\D", "", profile["id"])
    return int(digits) if digits else 0


def _missing_names(profiles: list[dict[str, str]]) -> bool:
    return any(not p["name"] for p in profiles)


def read_profile_catalog(session: Any, base: str, sid: str, extra: Any = None) -> list[dict[str, str]]:
    """Alle Zugangsprofile (``id``, ``name``) mit möglichst vollständigen Namen.

    Die Profilliste kommt aus ``kidPro`` (FRITZ!OS bis 8.2x); liefert die Box dort keine
    Profile (FRITZ!OS 8.40 antwortet für unbekannte Seiten mit der Übersicht), aus dem REST-Pfad
    ``filter_profile``, sonst aus ``extra``. Fehlende Namen werden in dieser Reihenfolge ergänzt:
    ``extra`` (die ``edit_device``-Antwort des Geräts - dort stehen sie so, wie die Box sie in der
    Auswahl zeigt) → ``filter_profile`` → ``kidLis`` → die festen Namen der Standardprofile
    (``DEFAULT_PROFILE_NAMES``). Weitere Quellen werden nur abgefragt, solange noch etwas fehlt.
    Bleibt ein Name leer, zeigt die Oberfläche die ID; einmal je Start steht dann ein Auszug der
    Seite ``kidPro`` im Protokoll (Warnung), damit das Format nachgetragen werden kann.
    """
    global _names_warned  # noqa: PLW0603 - einmalige Warnung je Start genügt
    page = data_lua(session, base, sid, "kidPro", SLOW_TIMEOUT)
    profiles = parse_profiles(page)
    device_names = parse_profile_names(extra) if extra is not None else {}
    if profiles:
        _fill_names(profiles, device_names)
    if not profiles or _missing_names(profiles):
        try:
            rest = parse_profiles(monitor_get(session, base, sid, FILTER_PROFILE_PATH))
        except Exception:  # noqa: BLE001 - Zusatzquelle (nur FRITZ!OS 8.x), Fehler sind hier harmlos
            rest = []
        if not profiles:
            profiles = sorted(rest, key=_profile_id_number)
            _fill_names(profiles, device_names)
        else:
            _fill_names(profiles, {p["id"]: p["name"] for p in rest})
    if not profiles and device_names:
        # Letzter Weg zur Liste: die Auswahl des Geräts selbst (zeigt nur die für dieses Gerät wählbaren Profile).
        profiles = [{"id": pid, "name": name} for pid, name in device_names.items()]
    if profiles and _missing_names(profiles):
        try:
            _fill_names(profiles, parse_profile_names(data_lua(session, base, sid, "kidLis", SLOW_TIMEOUT)))
        except Exception:  # noqa: BLE001 - Zusatzquelle, ein Fehler darf die Profilliste nicht kippen
            pass
    _fill_names(profiles, DEFAULT_PROFILE_NAMES)
    if profiles and _missing_names(profiles) and not _names_warned:
        _names_warned = True
        _LOGGER.warning(
            "Zugangsprofile ohne Namen (%s) - Auszug der Seite kidPro: %s",
            ", ".join(p["id"] for p in profiles if not p["name"]),
            _profile_excerpt(page),
        )
    return profiles


def parse_net_devices(payload: Any) -> list[dict[str, str]]:
    """Liest Geräte (``uid``, ``mac``, ``name``, ``ip``) aus ``netDev`` (JSON).

    Angenommen: ``data.active[]`` und ``data.passive[]`` mit ``UID``, ``mac``,
    ``name`` und ``ipv4.ip``. Einträge ohne UID oder MAC werden übersprungen.
    """
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return []
    devices: list[dict[str, str]] = []
    for group in ("active", "passive"):
        entries = data.get(group)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            uid = str(entry.get("UID") or "").strip()
            mac = normalize_mac(entry.get("mac"))
            if not uid or len(mac) != 12:
                continue
            ipv4 = entry.get("ipv4")
            ipv4 = ipv4 if isinstance(ipv4, dict) else {}
            devices.append(
                {
                    "uid": uid,
                    "mac": mac,
                    "name": str(entry.get("name") or "").strip(),
                    "ip": str(ipv4.get("ip") or ""),
                    # Reservierung ("immer die gleiche IPv4-Adresse"), falls die Box
                    # das Flag in der Liste mitliefert; sonst ``None`` (unbekannt).
                    "static": _flag(ipv4.get("static_dhcp", entry.get("static_dhcp"))),
                }
            )
    return devices


def _flag(value: Any) -> bool | None:
    """Schalterwert der Box (``"1"``/``"0"``, ``"on"``, ``true`` ...) oder ``None``, wenn unbekannt."""
    if value is None or value == "":
        return None
    text = str(value).strip().lower()
    if text in ("1", "on", "true", "yes"):
        return True
    if text in ("0", "off", "false", "no"):
        return False
    return None


# Geraeteliste ueber ``query.lua`` (Issue #31, feste Adresse): ``static_dhcp`` ist
# der Schalter "Diesem Netzwerkgeraet immer die gleiche IPv4-Adresse zuweisen".
# Nach Angabe eines Fremdprojekts (jvejmelka/fritzbox-static-lease, FRITZ!OS 8.25)
# liest die Weboberflaeche den Zustand ueber ``query.lua``; die genauen Feldnamen
# der Liste sind hier an keiner eigenen Box geprueft. Fehlt das Feld, bleibt der
# Wert ``None`` und die Karte zeigt weiter die Angabe der TR-064-Schnittstelle.
LANDEVICE_QUERY = "landevice:settings/landevice/list(name,ip,mac,UID,static_dhcp)"


def query_lua(
    session: Any,
    base: str,
    sid: str,
    query: str,
    key: str = "hosts",
    request_timeout: float = TIMEOUT,
) -> Any:
    """Ruft ``query.lua`` auf (``ValueError`` bei HTTP-Fehler oder ohne JSON)."""
    response = session.get(f"{base}/query.lua?sid={sid}&{key}={query}", timeout=request_timeout)
    if not response.ok:
        raise ValueError(f"query.lua: HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError as err:
        raise ValueError("query.lua lieferte kein JSON") from err


def parse_landevice_list(payload: Any) -> list[dict[str, Any]]:
    """Liest Geraete (``uid``, ``mac``, ``name``, ``ip``, ``static``) aus ``query.lua``.

    Erwartet ein JSON-Objekt, dessen (erste) Liste die Geraete enthaelt, oder
    direkt eine Liste. ``static`` ist ``True``/``False`` bei vorhandenem Feld
    ``static_dhcp``, sonst ``None``. Eintraege ohne MAC-Adresse werden uebersprungen.
    """
    entries: Any = None
    if isinstance(payload, dict):
        entries = next((v for v in payload.values() if isinstance(v, list)), None)
    elif isinstance(payload, list):
        entries = payload
    result: list[dict[str, Any]] = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        mac = normalize_mac(entry.get("mac"))
        if len(mac) != 12:
            continue
        result.append(
            {
                "uid": str(entry.get("UID") or "").strip(),
                "mac": mac,
                "name": str(entry.get("name") or "").strip(),
                "ip": str(entry.get("ip") or "").strip(),
                "static": _flag(entry.get("static_dhcp")),
            }
        )
    return result


def fetch_reservations(
    session: Any, base: str, user: str, password: str
) -> dict[str, Any]:
    """Liest, welche Geraete eine feste Zuweisung (Reservierung) haben (Issue #31).

    Gibt ``{"reserved": {mac_klein: bool}, "source": "query.lua"|"netDev"|None,
    "devices": n}`` zurueck. Zuerst ``query.lua``, ersatzweise ``netDev``. Liefert
    keiner der Wege das Feld, ist ``reserved`` leer (kein Fehler). Netzwerk- und
    Anmeldefehler laufen als ``ValueError``/Netzwerkfehler zum Aufrufer.
    """
    sid = login(session, base, user, password)
    try:
        devices: list[dict[str, Any]] = []
        source: str | None = None
        try:
            devices = parse_landevice_list(query_lua(session, base, sid, LANDEVICE_QUERY))
            source = "query.lua"
        except ValueError:
            devices = []
        if not any(d["static"] is not None for d in devices):
            try:
                alt = parse_net_devices(
                    data_lua(session, base, sid, "netDev", xhrId="all", useajax="1")
                )
            except ValueError:
                alt = []
            if any(d.get("static") is not None for d in alt):
                devices, source = alt, "netDev"
    finally:
        logout(session, base, sid)
    reserved = {
        d["mac"].lower(): bool(d["static"]) for d in devices if d.get("static") is not None
    }
    return {"reserved": reserved, "source": source if reserved else None, "devices": len(devices)}


# Online-Monitor (Datenraten je Geraet, seit 2.0.0b2): REST-Pfade der
# Weboberflaeche, so wie sie Fremdprojekte beschreiben (ioBroker-Forum:
# ``/api/v0/monitor/datasets`` listet die Datenquellen, ``.../macaddrs/subset0000``
# liefert deren Messreihen). Von AVM nicht dokumentiert, an keiner eigenen Box
# geprueft; ``traffic.py`` wertet die Antworten tolerant aus.
# Moegliche Wurzeln der Online-Monitor-Schnittstelle. Das Community-Skript nutzt
# "api/v0/monitor"; manche Boxen/FRITZ!OS-Staende antworten darauf mit
# "bad path: monitor/datasets" - dann wird die Variante unter "generic" probiert.
MONITOR_BASES = ("api/v0/monitor", "api/v0/generic/monitor")
MONITOR_SUBSET_NAME = "macaddrs/subset0000"


def monitor_get(session: Any, base: str, sid: str, path: str) -> Any:
    """GET auf einen REST-Pfad der Weboberflaeche (``ValueError`` bei HTTP-Fehler/ohne JSON)."""
    # Kopfzeilen wie im Community-Skript, das diese Schnittstelle nutzt (ioBroker-
    # Forum): ohne Content-Type/Referer antwortet die Box moeglicherweise mit 400.
    response = session.get(
        f"{base}/{path}",
        headers={
            "AUTHORIZATION": f"AVM-SID {sid}",
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Referer": f"{base}/",
        },
        timeout=TIMEOUT,
    )
    if not response.ok:
        # Ein Stueck der Antwort mitgeben: bei HTTP 400 steht dort oft der Grund.
        snippet = " ".join(str(getattr(response, "text", "") or "").split())[:200]
        suffix = f" - {snippet}" if snippet else ""
        raise ValueError(f"{path}: HTTP {response.status_code}{suffix}")
    try:
        return response.json()
    except ValueError as err:
        raise ValueError(f"{path}: keine JSON-Antwort") from err


MONITOR_ONLINE = "api/v0/monitor/online"


def _online_interval(payload: Any) -> float | None:
    """Abtastabstand (Sekunden) der Messreihe 0 aus ``monitor/online/subsets``."""
    for entry in payload if isinstance(payload, list) else []:
        if isinstance(entry, dict) and str(entry.get("id")) == "0":
            try:
                ms = float(entry.get("sampleInterval"))
            except (TypeError, ValueError):
                return None
            return ms / 1000 if ms > 0 else None
    return None


def fetch_monitor(
    session: Any,
    base: str,
    user: str,
    password: str,
    refresh_sources: bool,
    monitor_base: str | None = None,
) -> dict[str, Any]:
    """Liest die Messreihen des Online-Monitors (Raten je Geraet).

    Zwei Wege, in dieser Reihenfolge probiert (oder nur der in ``monitor_base``
    gemerkte):

    * ``"online"`` - ``api/v0/monitor/online/0`` (FRITZ!OS 8.x, an einer 8.40
      beobachtet): die Antwort enthaelt je Geraet MAC-Adresse und Raten.
      Ergebnis: ``{"mode": "online", "online": <Antwort>, "interval": <s>,
      "monitor_base": "online"}``.
    * Ausweichweg ``api/v0/monitor`` bzw. ``api/v0/generic/monitor`` mit
      ``datasets`` und ``macaddrs/subset0000`` (so beschreibt es ein
      Community-Skript fuer aeltere Staende), Ergebnis mit ``"mode": "legacy"``,
      ``subsets``, ``datasets`` (nur mit ``refresh_sources``) und ``landevices``.

    Fehler laufen als ``ValueError``/Netzwerkfehler zum Aufrufer; bei mehreren
    Fehlschlaegen stehen alle Meldungen im Text.
    """
    sid = login(session, base, user, password)
    try:
        errors: list[str] = []
        if monitor_base in (None, "online"):
            try:
                interval: float | None = None
                try:
                    interval = _online_interval(monitor_get(session, base, sid, f"{MONITOR_ONLINE}/subsets"))
                except ValueError:
                    interval = None
                online = monitor_get(session, base, sid, f"{MONITOR_ONLINE}/0")
                if not isinstance(online, dict) or "devices" not in online:
                    raise ValueError(f"{MONITOR_ONLINE}/0: unerwartetes Format")
                return {
                    "mode": "online",
                    "online": online,
                    "interval": interval,
                    "monitor_base": "online",
                    "subsets": None,
                    "datasets": None,
                    "landevices": None,
                }
            except ValueError as err:
                if monitor_base == "online":
                    raise
                errors.append(str(err))
        datasets: Any = None
        landevices: list[dict[str, Any]] | None = None
        roots = (monitor_base,) if monitor_base else MONITOR_BASES
        used = monitor_base
        if refresh_sources or not monitor_base or monitor_base == "online":
            for root in roots:
                try:
                    datasets = monitor_get(session, base, sid, f"{root}/datasets")
                except ValueError as err:
                    errors.append(str(err))
                    continue
                used = root
                break
            if used is None or used == "online":
                raise ValueError("; ".join(errors))
            try:
                landevices = parse_landevice_list(query_lua(session, base, sid, LANDEVICE_QUERY))
            except ValueError:
                landevices = []
        subsets = monitor_get(session, base, sid, f"{used}/{MONITOR_SUBSET_NAME}")
    finally:
        logout(session, base, sid)
    return {
        "mode": "legacy",
        "subsets": subsets,
        "datasets": datasets,
        "landevices": landevices,
        "monitor_base": used,
    }


def parse_device_profile(payload: Any) -> str | None:
    """Aktuelles Zugangsprofil aus ``edit_device`` (``…netAccess.kisi.profiles.selected``)."""
    node: Any = payload
    for key in ("data", "vars", "dev", "netAccess", "kisi", "profiles"):
        node = node.get(key) if isinstance(node, dict) else None
    selected = node.get("selected") if isinstance(node, dict) else None
    if isinstance(selected, str) and PROFILE_ID_RE.fullmatch(selected):
        return selected
    return None


def resolve_profile(profiles: list[dict[str, str]], reference: str) -> dict[str, str]:
    """Findet ein Profil per ID (``filtprof…``) oder Namen (ohne Groß-/Kleinschreibung)."""
    ref = str(reference or "").strip()
    if not ref:
        raise ValueError("Kein Profil angegeben")
    for profile in profiles:
        if profile["id"] == ref:
            return profile
    matches = [p for p in profiles if p["name"].casefold() == ref.casefold()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"Profilname '{ref}' ist nicht eindeutig - bitte die ID verwenden")
    names = ", ".join(p["name"] or p["id"] for p in profiles) or "keine gefunden"
    raise ValueError(f"Zugangsprofil '{ref}' nicht gefunden (vorhanden: {names})")


def _find_device(session: Any, base: str, sid: str, mac: str) -> dict[str, str]:
    """Findet ein Geraet (``uid``, ``mac``, ``name``, ``ip``) in der Weboberflaeche.

    Zuerst die schlanke Liste ueber ``query.lua`` (wie die Zuweisung einer festen
    Adresse, die auch bei grossen Netzen funktioniert); nur wenn das Geraet dort
    fehlt, die schwere Seite ``netDev`` - mit langer Lesezeit (``SLOW_TIMEOUT``).
    """
    key = normalize_mac(mac)
    try:
        for entry in parse_landevice_list(query_lua(session, base, sid, LANDEVICE_QUERY)):
            if entry["mac"] == key and entry["uid"]:
                return {"uid": entry["uid"], "mac": key, "name": entry["name"], "ip": entry["ip"]}
    except ValueError:
        pass
    devices = parse_net_devices(
        data_lua(session, base, sid, "netDev", SLOW_TIMEOUT, xhrId="all", useajax="1")
    )
    for device in devices:
        if device["mac"] == key:
            return device
    if not devices:
        raise ValueError("Die Geräteliste der Weboberfläche ließ sich nicht lesen (FRITZ!OS geändert?)")
    raise ValueError(f"Gerät {mac} ist der Weboberfläche nicht bekannt")


def _read_device_page(session: Any, base: str, sid: str, uid: str) -> Any:
    return data_lua(session, base, sid, "edit_device", SLOW_TIMEOUT, dev=uid)


def _read_profile(session: Any, base: str, sid: str, uid: str) -> str | None:
    return parse_device_profile(_read_device_page(session, base, sid, uid))


def list_profiles(session: Any, base: str, user: str, password: str) -> list[dict[str, str]]:
    """Alle Zugangsprofile der Box (``id``, ``name``)."""
    sid = login(session, base, user, password)
    try:
        profiles = read_profile_catalog(session, base, sid)
    finally:
        logout(session, base, sid)
    if not profiles:
        raise ValueError("Keine Zugangsprofile gefunden (FRITZ!OS geändert oder Seite nicht lesbar)")
    return profiles


def get_device_profile(
    session: Any, base: str, user: str, password: str, mac: str
) -> dict[str, Any]:
    """Aktuelles Zugangsprofil eines Geräts samt Liste aller Profile (``profile_liste``)."""
    sid = login(session, base, user, password)
    try:
        device = _find_device(session, base, sid, mac)
        device_page = _read_device_page(session, base, sid, device["uid"])
        current = parse_device_profile(device_page)
        profiles = read_profile_catalog(session, base, sid, extra=device_page)
    finally:
        logout(session, base, sid)
    return {
        "profile": current,
        "name": next((p["name"] for p in profiles if p["id"] == current and p["name"]), None),
        "device": device["name"],
        "profile_liste": profiles,
    }


def assign_profile(
    session: Any, base: str, user: str, password: str, mac: str, reference: str
) -> dict[str, str | None]:
    """Weist einem Gerät ein Zugangsprofil zu und prüft das Ergebnis nach.

    Gibt ``previous`` (ID oder ``None``), ``profile`` (ID), ``name`` zurück.
    Wirft ``ValueError``, wenn Profil/Gerät unbekannt sind, das aktuelle Profil
    nicht lesbar ist (dann wird NICHT geschrieben) oder die Box das Profil nach
    dem Schreiben nicht übernommen hat.

    Das Schreiben ist ein Formular-POST an ``page=edit_device`` mit
    ``dev``, ``dev_name``, ``kisi_profile`` und ``apply``. Ob die Box dabei
    weitere Geräteeinstellungen (z. B. feste IP-Zuweisung) unverändert lässt,
    ist an keiner Box geprüft.
    """
    sid = login(session, base, user, password)
    try:
        profiles = read_profile_catalog(session, base, sid)
        target = resolve_profile(profiles, reference)
        device = _find_device(session, base, sid, mac)
        previous = _read_profile(session, base, sid, device["uid"])
        if previous is None:
            raise ValueError(
                "Das aktuelle Zugangsprofil des Geräts ist nicht lesbar - es wird nichts geändert"
            )
        if previous != target["id"]:
            response = session.post(
                f"{base}/data.lua",
                data={
                    "sid": sid,
                    "dev": device["uid"],
                    "dev_name": device["name"],
                    "kisi_profile": target["id"],
                    "page": "edit_device",
                    "apply": "true",
                },
                timeout=SLOW_TIMEOUT,
            )
            if not response.ok:
                raise ValueError(f"data.lua (edit_device): HTTP {response.status_code}")
            now = _read_profile(session, base, sid, device["uid"])
            if now != target["id"]:
                raise ValueError(
                    "Die FRITZ!Box hat das Zugangsprofil nicht übernommen "
                    f"(jetzt: {now or 'unbekannt'}) - Aufbau der Weboberfläche geändert?"
                )
    finally:
        logout(session, base, sid)
    return {"previous": previous, "profile": target["id"], "name": target["name"]}


def fetch_online_extras(session: Any, base: str, user: str, password: str) -> dict[str, Any]:
    """Liest Verbindungsdetails und Online-Zaehler (je Teil unabhaengig; Fehler stehen in ``errors``)."""
    sid = login(session, base, user, password)
    result: dict[str, Any] = {"connections": None, "inetstat": None, "errors": []}
    try:
        for key, path in (("connections", "api/v0/generic/connections"), ("inetstat", "api/v0/generic/inetstat")):
            try:
                result[key] = monitor_get(session, base, sid, path)
            except ValueError as err:
                result["errors"].append(str(err))
    finally:
        logout(session, base, sid)
    return result
