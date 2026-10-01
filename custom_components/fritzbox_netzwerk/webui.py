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
import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urlsplit

EMPTY_SID = "0000000000000000"
TIMEOUT = 10


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


def data_lua(session: Any, base: str, sid: str, page: str, **fields: str) -> Any:
    """Ruft ``data.lua`` auf und liefert die Antwort (JSON-Objekt, sonst Text)."""
    form = {"xhr": "1", "sid": sid, "lang": "de", "page": page, "no_sidrenew": ""}
    form.update(fields)
    response = session.post(f"{base}/data.lua", data=form, timeout=TIMEOUT)
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
_TAG_RE = re.compile(r"<[^>]*\bvalue=\"(filtprof\d+)\"[^>]*>", re.IGNORECASE)
_NAME_RE = re.compile(r"\bdata-name=\"([^\"]*)\"", re.IGNORECASE)


def normalize_mac(mac: Any) -> str:
    """Nur Hex-Zeichen in Großschreibung (Schlüssel zum Vergleich)."""
    return re.sub(r"[^0-9A-Fa-f]", "", str(mac or "")).upper()


def parse_profiles(page: Any) -> list[dict[str, str]]:
    """Liest die Zugangsprofile (``id``, ``name``) aus der HTML-Seite ``kidPro``.

    Erwartet Markierungen mit ``value="filtprofNNN"`` und ``data-name="…"`` im
    selben Tag (Attributreihenfolge egal). Doppelte IDs zählen einmal.
    """
    text = page if isinstance(page, str) else ""
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in _TAG_RE.finditer(text):
        profile_id = match.group(1)
        if profile_id in seen:
            continue
        name = _NAME_RE.search(match.group(0))
        seen.add(profile_id)
        result.append({"id": profile_id, "name": html.unescape(name.group(1)).strip() if name else ""})
    return result


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
            devices.append(
                {
                    "uid": uid,
                    "mac": mac,
                    "name": str(entry.get("name") or "").strip(),
                    "ip": str((ipv4 or {}).get("ip") or "") if isinstance(ipv4, dict) else "",
                }
            )
    return devices


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
    key = normalize_mac(mac)
    devices = parse_net_devices(
        data_lua(session, base, sid, "netDev", xhrId="all", useajax="1")
    )
    for device in devices:
        if device["mac"] == key:
            return device
    if not devices:
        raise ValueError("Die Geräteliste der Weboberfläche ließ sich nicht lesen (FRITZ!OS geändert?)")
    raise ValueError(f"Gerät {mac} ist der Weboberfläche nicht bekannt")


def _read_profile(session: Any, base: str, sid: str, uid: str) -> str | None:
    return parse_device_profile(data_lua(session, base, sid, "edit_device", dev=uid))


def list_profiles(session: Any, base: str, user: str, password: str) -> list[dict[str, str]]:
    """Alle Zugangsprofile der Box (``id``, ``name``)."""
    sid = login(session, base, user, password)
    try:
        profiles = parse_profiles(data_lua(session, base, sid, "kidPro"))
    finally:
        logout(session, base, sid)
    if not profiles:
        raise ValueError("Keine Zugangsprofile gefunden (FRITZ!OS geändert oder Seite nicht lesbar)")
    return profiles


def get_device_profile(
    session: Any, base: str, user: str, password: str, mac: str
) -> dict[str, str | None]:
    """Aktuelles Zugangsprofil eines Geräts (``profile`` ist ID, ``name`` der Anzeigename)."""
    sid = login(session, base, user, password)
    try:
        device = _find_device(session, base, sid, mac)
        current = _read_profile(session, base, sid, device["uid"])
        names = {p["id"]: p["name"] for p in parse_profiles(data_lua(session, base, sid, "kidPro"))}
    finally:
        logout(session, base, sid)
    return {"profile": current, "name": names.get(current or "", None), "device": device["name"]}


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
        profiles = parse_profiles(data_lua(session, base, sid, "kidPro"))
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
                timeout=TIMEOUT,
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
