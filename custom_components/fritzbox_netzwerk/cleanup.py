# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): b690c24fcf2f7eb09da703b39e6e23e8831fa50e533bb3dbc69e8b63d766c36c
"""Ungenutzte Verbindungen aus der Geraeteliste der FRITZ!Box entfernen (seit 2.0.2).

Entspricht an der FRITZ!Box: Heimnetz -> Netzwerk -> Netzwerkverbindungen, ganz unten
"Alle ungenutzten Verbindungen entfernen" (die Box schreibt dazu: Netzwerkgeraete
mit individuellen Einstellungen bleiben dabei erhalten).

BEOBACHTET (FRITZ!Box 5690 Pro, FRITZ!OS 8.40 BETA, nur lesend): Der Knopf der
Weboberflaeche sendet

    PUT /api/v0/generic/landevice
    AUTHORIZATION: AVM-SID <sid>      Client-Name: WebGUI
    {"cleanup_landevices": "1"}

Die Anfrage wurde im Browser abgefangen, BEVOR sie die Box erreichte; ausgefuehrt wurde
sie dort nicht. Ob und welche Eintraege die Box daraufhin entfernt, ist an einer echten
Box deshalb NICHT geprueft. Aeltere FRITZ!OS-Staende kennen die Route moeglicherweise nicht
(HTTP-Fehler) - dann wird nichts geaendert und der Fehler gemeldet; einen geratenen
Ersatzweg gibt es bewusst nicht.

Das Modul hat keine Home-Assistant- und keine fritzconnection-Importe.
"""
from __future__ import annotations

from typing import Any

from .dns_settings import ConfirmationRequired, DnsSettingsError, SessionExpired, api_request
from .webui import login, logout

LANDEVICE_ENDPOINT = "landevice"
CLEANUP_BODY = {"cleanup_landevices": "1"}


class CleanupError(ValueError):
    """Das Entfernen der ungenutzten Verbindungen ist fehlgeschlagen."""


def _entries(payload: Any) -> list[dict[str, Any]] | None:
    """Eintraege der Geraeteliste (``landevice``-Feld) oder ``None`` bei fremdem Aufbau."""
    if not isinstance(payload, dict) or not isinstance(payload.get("landevice"), list):
        return None
    return [entry for entry in payload["landevice"] if isinstance(entry, dict)]


def _uid(entry: dict[str, Any]) -> str:
    return str(entry.get("UID") or entry.get("uid") or "")


def _label(entry: dict[str, Any]) -> str:
    return str(entry.get("name") or entry.get("friendly_name") or _uid(entry) or "?")


def _snapshot(session: Any, base: str, sid: str) -> list[dict[str, Any]] | None:
    try:
        return _entries(api_request(session, base, sid, "GET", LANDEVICE_ENDPOINT))
    except (DnsSettingsError, OSError):
        return None


def summarize_removed(
    before: list[dict[str, Any]] | None, after: list[dict[str, Any]] | None
) -> dict[str, Any]:
    """Vergleicht die Geraeteliste vor und nach dem Aufraeumen (reine Funktion)."""
    if before is None or after is None:
        return {"vorher": None if before is None else len(before),
                "nachher": None if after is None else len(after),
                "entfernt": None, "geraete": []}
    kept = {_uid(entry) for entry in after}
    gone = [entry for entry in before if _uid(entry) and _uid(entry) not in kept]
    return {
        "vorher": len(before),
        "nachher": len(after),
        "entfernt": len(gone),
        "geraete": sorted(_label(entry) for entry in gone),
    }


def remove_unused_connections(session: Any, base: str, user: str, password: str) -> dict[str, Any]:
    """Loest "Alle ungenutzten Verbindungen entfernen" aus und meldet, was verschwunden ist."""
    sid = login(session, base, user, password)
    try:
        before = _snapshot(session, base, sid)
        try:
            api_request(session, base, sid, "PUT", LANDEVICE_ENDPOINT, CLEANUP_BODY)
        except ConfirmationRequired as err:
            raise CleanupError(str(err)) from err
        except SessionExpired as err:
            raise CleanupError(str(err)) from err
        except DnsSettingsError as err:
            raise CleanupError(
                f"Die FRITZ!Box hat die Anfrage abgelehnt ({err}). Vermutlich kennt diese "
                "FRITZ!OS-Version die Funktion nicht über diese Schnittstelle - es wurde nichts geändert."
            ) from err
        after = _snapshot(session, base, sid)
        result = summarize_removed(before, after)
        result["geprueft"] = result["entfernt"] is not None
        if not result["geprueft"]:
            result["hinweis"] = (
                "Die Geräteliste der Box ließ sich nicht vor und nach dem Aufräumen vergleichen - "
                "bitte in der FRITZ!Box unter Heimnetz → Netzwerk kontrollieren."
            )
        return result
    finally:
        logout(session, base, sid)
