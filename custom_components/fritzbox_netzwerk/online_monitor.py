# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): fdbb707e982f29c6c2d29599c7ebbf7c5703c0a583d86aa54ee73c1480c2041b
"""Aufbereitung der Online-Monitor-Daten fuer die Karte (seit 2.0.0b7).

Drei Ansichten, jeweils aus einer Antwort der Weboberflaeche der Box:

* **Online-Monitor** - aktuelle Raten gesamt, nach Kategorie und je Geraet aus
  ``api/v0/monitor/online/0`` (Aufbau an einer FRITZ!OS 8.40 beobachtet).
* **Verbindungsdetails** - ``api/v0/generic/connections`` (Aufbau an einer
  FRITZ!OS 8.40 beobachtet). Zugangsname und Passwort werden NIE uebernommen.
* **Online-Zaehler** - ``api/v0/generic/inetstat``. Der genaue Aufbau ist an
  keiner eigenen Box geprueft: der Leser ist deshalb bewusst tolerant und
  uebernimmt nur Zaehler, die er sicher einem Zeitraum und einer Richtung
  zuordnen kann. Alles andere bleibt leer (die Karte zeigt dann einen Hinweis).

Das Modul enthaelt keine Home-Assistant-Importe.
"""
from __future__ import annotations

import math
import re
from typing import Any, Final

SERIES_POINTS: Final = 30
TOP_DEVICES: Final = 8

_MAC_UID = re.compile(r"^mac([0-9a-f]{12})$")

# Felder von ``generic/connections``, die uebernommen werden (Zugangsdaten nicht).
_CONNECTION_FIELDS: Final = (
    "name",
    "media_type",
    "enable",
    "is_active_internet_connection",
    "conn_time",
    "conn_date",
    "ip4_connstatus",
    "ip4_masqaddr",
    "ip4_gateway",
    "ip4_first_dns",
    "ip4_second_dns",
    "ip4_uptime",
    "ip6_connstatus",
    "ip6_addr",
    "ip6_prefix",
    "ip6_first_dns",
    "ip6_second_dns",
    "ip6_uptime",
    "max_speed_down",
    "max_speed_up",
    "providername",
)

PERIODS: Final = {
    "today": "today",
    "yesterday": "yesterday",
    "thisweek": "this_week",
    "lastweek": "last_week",
    "thismonth": "this_month",
    "lastmonth": "last_month",
    "total": "total",
}


def _num(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _series(values: Any) -> list[float]:
    return [n for n in (_num(v) for v in values) if n is not None] if isinstance(values, list) else []


def parse_overview(payload: Any, factor: float = 1.0) -> dict[str, Any] | None:
    """Aktuelle Raten (Byte/s) gesamt, je Kategorie und je Geraet.

    ``factor`` rechnet die Einheit der Box in Byte/s um (1.0 Byte/s, 0.125 Bit/s).
    Ohne erkennbare Geraeteliste: ``None``.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("devices"), list):
        return None
    down_total: list[float] = []
    up_total: list[float] = []
    top: list[dict[str, Any]] = []

    def add(total: list[float], values: list[float]) -> None:
        for i, v in enumerate(values):
            if i < len(total):
                total[i] += v
            else:
                total.append(v)

    for device in payload["devices"]:
        if not isinstance(device, dict):
            continue
        down = _series(device.get("downstream"))
        up = _series(device.get("upstream"))
        add(down_total, down)
        add(up_total, up)
        found = _MAC_UID.match(str(device.get("UID") or "").strip())
        if found and (down or up):
            top.append(
                {
                    "mac": ":".join(found.group(1)[i : i + 2] for i in range(0, 12, 2)).upper(),
                    "down": round((down[-1] if down else 0) * factor, 1),
                    "up": round((up[-1] if up else 0) * factor, 1),
                }
            )
    top.sort(key=lambda e: e["down"] + e["up"], reverse=True)
    categories: list[dict[str, Any]] = []
    for cat in payload.get("categories") or []:
        if not isinstance(cat, dict):
            continue
        down = _series(cat.get("downstream"))
        up = _series(cat.get("upstream"))
        if not (down or up):
            continue
        categories.append(
            {
                "type": str(cat.get("type") or "")[:24],
                "down": round((down[-1] if down else 0) * factor, 1),
                "up": round((up[-1] if up else 0) * factor, 1),
            }
        )

    def scaled(values: list[float]) -> list[float]:
        return [round(v * factor, 1) for v in values[-SERIES_POINTS:]]

    return {
        "updated": _num(payload.get("lastSampleTime")),
        "down": scaled(down_total)[-1] if down_total else None,
        "up": scaled(up_total)[-1] if up_total else None,
        "series_down": scaled(down_total),
        "series_up": scaled(up_total),
        "categories": categories,
        "top": top[:TOP_DEVICES],
    }


def parse_connections(payload: Any) -> list[dict[str, Any]]:
    """Verbindungsdetails; nur aktive/aktivierte Verbindungen, ohne Zugangsdaten."""
    rows = payload.get("connection") if isinstance(payload, dict) else None
    result: list[dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        entry = {key: str(row[key]) for key in _CONNECTION_FIELDS if key in row and row[key] not in (None, "")}
        if str(row.get("enable")) != "1" and str(row.get("is_active_internet_connection")) != "1":
            continue
        if entry.get("name"):
            result.append(entry)
    return result


def _norm(key: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def _period_of(*names: str) -> str | None:
    for name in names:
        n = _norm(name)
        # laengere Namen zuerst, damit "lastweek" nicht als "week" o. ae. gilt
        for token in sorted(PERIODS, key=len, reverse=True):
            if token in n:
                return PERIODS[token]
    return None


def _direction(name: str) -> str | None:
    n = _norm(name)
    if any(skip in n for skip in ("packet", "pkt", "conn", "time", "dur", "count")):
        return None
    if any(t in n for t in ("recv", "receiv", "rcv", "down", "incoming")):
        return "down"
    if any(t in n for t in ("sent", "send", "upstream", "up", "outgoing")):
        return "up"
    return None


def _walk(node: Any, context: str, out: dict[str, dict[str, float]], parts: dict[tuple[str, str, str], dict[str, float]]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                _walk(value, f"{context}/{key}", out, parts)
                continue
            number = _num(value)
            if number is None:
                continue
            period = _period_of(str(key), *reversed(context.split("/")))
            direction = _direction(str(key))
            if not period or not direction:
                continue
            n = _norm(key)
            if "high" in n:
                parts.setdefault((period, direction, n.replace("high", "")), {})["high"] = number
            elif "low" in n:
                parts.setdefault((period, direction, n.replace("low", "")), {})["low"] = number
            else:
                out.setdefault(period, {})[direction] = out.get(period, {}).get(direction, 0) + number
    elif isinstance(node, list):
        for i, item in enumerate(node):
            label = ""
            if isinstance(item, dict):
                label = str(item.get("UID") or item.get("name") or item.get("period") or "")
            _walk(item, f"{context}/{label or i}", out, parts)


def parse_inetstat(payload: Any) -> dict[str, dict[str, float]]:
    """Online-Zaehler als ``{zeitraum: {"down": bytes, "up": bytes}}`` (tolerant, siehe Modulkopf)."""
    out: dict[str, dict[str, float]] = {}
    parts: dict[tuple[str, str, str], dict[str, float]] = {}
    _walk(payload, "", out, parts)
    for (period, direction, _base), pair in parts.items():
        if "low" in pair or "high" in pair:
            value = pair.get("high", 0) * 4294967296 + pair.get("low", 0)
            out.setdefault(period, {})[direction] = out.get(period, {}).get(direction, 0) + value
    return {p: {d: round(v) for d, v in dirs.items()} for p, dirs in out.items() if p in PERIODS.values()}


def inetstat_shape(payload: Any) -> dict[str, Any]:
    """Aufbau der Zaehler-Antwort fuer die Diagnose (nur Schluesselnamen, keine Werte)."""
    if isinstance(payload, dict):
        keys = sorted(str(k) for k in payload)[:20]
        nested = {str(k): sorted(str(x) for x in v)[:12] for k, v in payload.items() if isinstance(v, dict)}
        return {"top": "dict", "keys": keys, "nested": dict(list(nested.items())[:8])}
    if isinstance(payload, list):
        first = payload[0] if payload else None
        return {"top": "list", "len": len(payload), "first_keys": sorted(str(k) for k in first)[:20] if isinstance(first, dict) else None}
    return {"top": type(payload).__name__}
