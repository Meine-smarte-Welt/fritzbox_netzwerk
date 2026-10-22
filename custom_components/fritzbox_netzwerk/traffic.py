# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 97168147bbb8c207cf51b8a04aef17cfd6531d0245e820e96638d69bc2e4778e
"""Datenverbrauch je Geraet ueber 7 Tage (EXPERIMENTELL, seit 2.0.0b2).

Quelle ist der Online-Monitor der Weboberflaeche (FRITZ!OS ab 7.90/8.0,
"Internet -> Online-Monitor -> Einzelne Geraete"). Er liefert je Geraet
**Datenraten** (Downstream/Upstream), im Abstand von 5 Sekunden abgetastet,
**kein Volumen**, und nur fuer Geraete, bei denen in der Box "Internet-
Datenraten speichern" eingeschaltet ist. Dieses Modul rechnet die Raten ueber
die Zeitstempel zu Bytes auf und fuehrt Tagessummen fuer die letzten Tage.

Die Schnittstelle (``/api/v0/monitor/datasets`` und ``.../macaddrs/subset0000``)
ist von AVM nicht dokumentiert. Der Aufbau ist nur aus Fremdprojekten bekannt
(ioBroker-Forum) und an KEINER eigenen Box geprueft - das gilt insbesondere
fuer die **Einheit** der Messwerte (angenommen Byte/s, umstellbar auf Bit/s),
die Laenge des Zeitfensters je Abruf und die Zeitstempel (Sekunden oder
Millisekunden werden beide erkannt). Alle Funktionen sind deshalb tolerant:
Unbekanntes wird uebersprungen, nie geraten.

Das Modul enthaelt keine Home-Assistant-Importe.
"""
from __future__ import annotations

import math
import re
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from typing import Any, Final

SAMPLE_SECONDS: Final = 5.0
# Wie viele Tage gespeichert bleiben (angezeigt werden die letzten 7).
KEEP_DAYS: Final = 8
WEEK_DAYS: Final = 7

UNIT_BYTES: Final = "bytes"
UNIT_BITS: Final = "bits"
UNITS: Final = (UNIT_BYTES, UNIT_BITS)

_MAC_SEPARATED = re.compile(r"(?<![0-9a-f])(?:[0-9a-f]{2}[:\-]){5}[0-9a-f]{2}(?![0-9a-f])", re.IGNORECASE)
_MAC_PLAIN = re.compile(r"(?<![0-9a-f])[0-9a-f]{12}(?![0-9a-f])", re.IGNORECASE)


def _mac_key(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isalnum()).lower()


def _rows(payload: Any) -> list[Any]:
    """Die (erste) Liste einer Antwort: direkt, unter ``data`` oder als erster Listenwert."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return data
        for value in payload.values():
            if isinstance(value, list):
                return value
    return []


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return number


def _direction(kind: Any) -> str | None:
    text = str(kind or "").lower()
    if "down" in text:
        return "down"
    if "up" in text:
        return "up"
    return None


def mac_from_name(name: Any) -> str:
    """MAC-Schluessel, falls der Datenquellenname selbst eine MAC-Adresse enthaelt, sonst ``""``."""
    text = str(name or "")
    match = _MAC_SEPARATED.search(text) or _MAC_PLAIN.search(text)
    return _mac_key(match.group(0)) if match else ""


def build_source_map(
    datasets_payload: Any, landevices: list[dict[str, Any]] | None
) -> tuple[dict[str, dict[str, str]], dict[str, int]]:
    """Ordnet Datenquellen Geraeten und der Richtung zu.

    ``datasets_payload`` ist die Antwort von ``/api/v0/monitor/datasets``,
    ``landevices`` die Geraeteliste (``uid``, ``mac``) aus ``query.lua``.
    Gibt ``({datenquelle: {"mac": schluessel, "kind": "down"|"up"}}, zaehler)``
    zurueck. Quellen ohne Geraetebezug (z. B. die DSL-Gesamtkurve) und solche,
    die sich keinem Geraet zuordnen lassen, fehlen im Ergebnis.
    """
    uid_to_mac = {
        str(d.get("uid")): _mac_key(d.get("mac"))
        for d in landevices or []
        if d.get("uid") and d.get("mac")
    }
    mapping: dict[str, dict[str, str]] = {}
    counts = {"sources": 0, "per_device": 0, "resolved": 0, "unresolved": 0, "no_direction": 0}
    for dataset in _rows(datasets_payload):
        if not isinstance(dataset, dict):
            continue
        for source in dataset.get("dataSources") or []:
            if not isinstance(source, dict):
                continue
            counts["sources"] += 1
            name = str(source.get("dataSourceName") or "").strip()
            uid = str(source.get("landeviceUid") or "").strip()
            if not name:
                continue
            by_name = mac_from_name(name)
            if not uid and not by_name:
                continue  # keine Geraetekurve (z. B. DSL gesamt)
            counts["per_device"] += 1
            kind = _direction(source.get("type"))
            if kind is None:
                counts["no_direction"] += 1
                continue
            mac = uid_to_mac.get(uid) or by_name
            if not mac:
                counts["unresolved"] += 1
                continue
            counts["resolved"] += 1
            mapping[name] = {"mac": mac, "kind": kind}
    return mapping, counts


def _timestamp_seconds(value: Any) -> float | None:
    number = _number(value)
    if number is None or number <= 0:
        return None
    return number / 1000.0 if number > 1e11 else number


def parse_subsets(payload: Any) -> list[dict[str, Any]]:
    """Liest die Messreihen: ``name``, ``end`` (Sekunden), ``interval``, ``values``."""
    result: list[dict[str, Any]] = []
    for entry in _rows(payload):
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("dataSourceName") or "").strip()
        end = _timestamp_seconds(entry.get("timestamp"))
        measurements = entry.get("measurements")
        if not name or end is None or not isinstance(measurements, list):
            continue
        interval = _number(entry.get("sampleInterval") or entry.get("interval"))
        if interval is None or not 1 <= interval <= 3600:
            interval = SAMPLE_SECONDS
        result.append(
            {
                "name": name,
                "end": end,
                "interval": float(interval),
                "values": [_number(value) for value in measurements],
            }
        )
    return result


def traffic_shape(datasets_payload: Any, subsets_payload: Any) -> dict[str, Any]:
    """Aufbau der Antworten fuer den Diagnose-Download (Schluesselnamen, Anzahlen, ein paar Raten).

    Enthaelt keine Namen, Adressen oder Datenquellennamen. Hilft zu pruefen,
    ob die Annahmen zu Aufbau, Zeitstempel und Einheit stimmen. Die Felder zu
    ``datasets`` fehlen, wenn ``datasets_payload`` ``None`` ist (nicht abgerufen).
    """
    shape: dict[str, Any] = {}
    if datasets_payload is not None:
        rows = _rows(datasets_payload)
        first = rows[0] if rows and isinstance(rows[0], dict) else {}
        sources = [
            src
            for row in rows
            if isinstance(row, dict)
            for src in (row.get("dataSources") or [])
            if isinstance(src, dict)
        ]
        shape.update(
            datasets_top=type(datasets_payload).__name__,
            datasets=len(rows),
            dataset_keys=sorted(str(k) for k in first)[:12],
            source_keys=sorted(str(k) for k in (sources[0] if sources else {}))[:12],
            source_types=sorted({str(s.get("type")) for s in sources})[:6],
            name_has_mac=any(mac_from_name(s.get("dataSourceName")) for s in sources),
            sources_with_uid=sum(1 for s in sources if s.get("landeviceUid")),
        )
    rows = _rows(subsets_payload)
    first = rows[0] if rows and isinstance(rows[0], dict) else {}
    measurements = first.get("measurements")
    numbers = [n for n in (_number(v) for v in (measurements or [])) if n is not None]
    timestamp = _number(first.get("timestamp"))
    shape.update(
        subsets_top=type(subsets_payload).__name__,
        subsets=len(rows),
        subset_keys=sorted(str(k) for k in first)[:12],
        measurements_len=len(measurements) if isinstance(measurements, list) else None,
        timestamp_digits=len(str(int(timestamp))) if timestamp else None,
        sample_values=[round(n, 1) for n in numbers[-6:]],
    )
    return shape


_ONLINE_UID = re.compile(r"^mac([0-9a-f]{12})$", re.IGNORECASE)


def parse_online(payload: Any, interval: float | None = None) -> tuple[dict[str, dict[str, str]], dict[str, int], list[dict[str, Any]]]:
    """Liest die Antwort von ``api/v0/monitor/online/<id>`` (FRITZ!OS 8.x, an einer 8.40 beobachtet).

    Aufbau: ``{"lastSampleTime": <s>, "categories": [...], "devices": [{"UID":
    "mac<12 Hex>", "landeviceUid": "landeviceNNN", "upstream": [...],
    "downstream": [...]}]}`` - die Werte sind Raten je Messzeitpunkt, der
    Zeitstempel ist der der neuesten Messung. Gibt ``(Zuordnung, Zaehler,
    Messreihen)`` im selben Format wie ``build_source_map``/``parse_subsets``
    zurueck, damit ``TrafficLedger.ingest`` beide Wege gleich verarbeitet.
    """
    mapping: dict[str, dict[str, str]] = {}
    counts = {"sources": 0, "per_device": 0, "resolved": 0, "unresolved": 0, "no_direction": 0}
    raw: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        return mapping, counts, []
    last = payload.get("lastSampleTime")
    step = interval if interval and 1 <= interval <= 3600 else SAMPLE_SECONDS
    for device in payload.get("devices") or []:
        if not isinstance(device, dict):
            continue
        counts["per_device"] += 1
        found = _ONLINE_UID.match(str(device.get("UID") or "").strip())
        if not found:
            counts["unresolved"] += 1
            continue
        key = found.group(1).lower()
        counts["resolved"] += 1
        for field, kind in (("downstream", "down"), ("upstream", "up")):
            values = device.get(field)
            if not isinstance(values, list) or not values:
                continue
            name = f"{key}:{kind}"
            counts["sources"] += 1
            mapping[name] = {"mac": key, "kind": kind}
            raw.append(
                {"dataSourceName": name, "timestamp": last, "measurements": values, "sampleInterval": step}
            )
    return mapping, counts, parse_subsets(raw)


def online_shape(payload: Any, interval: float | None) -> dict[str, Any]:
    """Aufbau der ``online``-Antwort fuer den Diagnose-Download (ohne Namen/Adressen)."""
    shape: dict[str, Any] = {"mode": "online", "interval_s": interval}
    if not isinstance(payload, dict):
        shape["top"] = type(payload).__name__
        return shape
    devices = [d for d in payload.get("devices") or [] if isinstance(d, dict)]
    with_values = [
        d for d in devices if any(_number(v) is not None for v in (d.get("downstream") or []))
    ]
    sample: list[float] = []
    for device in with_values:
        sample = [n for n in (_number(v) for v in (device.get("downstream") or [])) if n is not None][-6:]
        if any(sample):
            break
    last = _number(payload.get("lastSampleTime"))
    series = with_values[0].get("downstream") if with_values else None
    shape.update(
        keys=sorted(str(k) for k in payload)[:12],
        devices=len(devices),
        devices_with_mac_uid=sum(1 for d in devices if _ONLINE_UID.match(str(d.get("UID") or ""))),
        devices_with_values=len(with_values),
        categories=sorted({str(c.get("type")) for c in payload.get("categories") or [] if isinstance(c, dict)})[:8],
        series_len=len(series) if isinstance(series, list) else None,
        timestamp_digits=len(str(int(last))) if last else None,
        sample_values=[round(n, 1) for n in sample],
    )
    return shape


def _utc_day(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


class TrafficLedger:
    """Fuehrt Tagessummen (Bytes, abwaerts/aufwaerts) je Geraet und merkt sich den Abrufstand."""

    def __init__(
        self,
        unit: str = UNIT_BYTES,
        day_of: Callable[[float], str] | None = None,
    ) -> None:
        self.unit = unit if unit in UNITS else UNIT_BYTES
        self._day_of = day_of or _utc_day
        # {"JJJJ-MM-TT": {mac_schluessel: [bytes_ab, bytes_auf]}}
        self.days: dict[str, dict[str, list[float]]] = {}
        # {datenquelle: Zeitstempel (Sekunden) des zuletzt eingerechneten Messwerts}
        self.cursors: dict[str, float] = {}
        self.stats: dict[str, Any] = {
            "last_samples": 0,
            "last_sources": 0,
            "window_seconds": 0.0,
            "gap_seconds_total": 0.0,
            "resets": 0,
            "last_end": None,
        }

    @property
    def _factor(self) -> float:
        return 1.0 if self.unit == UNIT_BYTES else 0.125

    def ingest(
        self, source_map: dict[str, dict[str, str]], subsets: list[dict[str, Any]]
    ) -> int:
        """Rechnet neue Messwerte ein und liefert, wie viele es waren."""
        total = 0
        sources = 0
        window = 0.0
        for subset in subsets:
            info = source_map.get(subset["name"])
            if not info:
                continue
            sources += 1
            values = subset["values"]
            interval = subset["interval"]
            end = subset["end"]
            window = max(window, len(values) * interval)
            cursor = self.cursors.get(subset["name"])
            if cursor is not None and end < cursor - 3600:
                # Die Uhr der Box ging zurueck (Neustart, Zeitumstellung der Box):
                # neu aufsetzen, statt alle weiteren Werte zu verwerfen.
                cursor = None
                self.stats["resets"] += 1
            first_new: float | None = None
            for index, value in enumerate(values):
                moment = end - (len(values) - 1 - index) * interval
                if cursor is not None and moment <= cursor + 1e-6:
                    continue
                if first_new is None:
                    first_new = moment
                if value is None:
                    continue
                day = self.days.setdefault(self._day_of(moment), {})
                pair = day.setdefault(info["mac"], [0.0, 0.0])
                pair[0 if info["kind"] == "down" else 1] += value * self._factor * interval
                total += 1
            if cursor is not None and first_new is not None and first_new - cursor > 3 * interval:
                self.stats["gap_seconds_total"] += first_new - cursor - interval
            if cursor is None or end > cursor:
                self.cursors[subset["name"]] = end
        self.stats.update(
            last_samples=total,
            last_sources=sources,
            window_seconds=window,
            last_end=max((s["end"] for s in subsets), default=self.stats.get("last_end")),
        )
        return total

    def prune(self, today: str) -> None:
        """Entfernt Tage, die aelter als ``KEEP_DAYS`` sind, und Abrufstaende ohne Tagesdaten nicht."""
        limit = (date.fromisoformat(today) - timedelta(days=KEEP_DAYS - 1)).isoformat()
        for key in [k for k in self.days if k < limit]:
            del self.days[key]

    def summary(self, today: str) -> dict[str, dict[str, Any]]:
        """Summen je Geraet fuer die letzten ``WEEK_DAYS`` Tage bis einschliesslich ``today``."""
        end = date.fromisoformat(today)
        labels = [(end - timedelta(days=offset)).isoformat() for offset in range(WEEK_DAYS - 1, -1, -1)]
        result: dict[str, dict[str, Any]] = {}
        for index, label in enumerate(labels):
            for mac, (down, up) in self.days.get(label, {}).items():
                entry = result.setdefault(
                    mac,
                    {"week_down": 0.0, "week_up": 0.0, "today": 0.0, "days": [0.0] * WEEK_DAYS},
                )
                entry["week_down"] += down
                entry["week_up"] += up
                entry["days"][index] = down + up
                if label == today:
                    entry["today"] = down + up
        for entry in result.values():
            entry["week"] = entry["week_down"] + entry["week_up"]
            for key in ("week_down", "week_up", "week", "today"):
                entry[key] = round(entry[key])
            entry["days"] = [round(v) for v in entry["days"]]
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit": self.unit,
            "days": {
                day: {mac: [round(a, 1), round(b, 1)] for mac, (a, b) in macs.items()}
                for day, macs in self.days.items()
            },
            "cursors": dict(self.cursors),
            "gap_seconds_total": self.stats["gap_seconds_total"],
        }

    def load(self, stored: Any) -> None:
        """Uebernimmt gespeicherte Daten (ungueltige Teile werden uebersprungen)."""
        if not isinstance(stored, dict):
            return
        days = stored.get("days")
        if isinstance(days, dict):
            for day, macs in days.items():
                if not isinstance(macs, dict):
                    continue
                try:
                    date.fromisoformat(str(day))
                except ValueError:
                    continue
                for mac, pair in macs.items():
                    if isinstance(pair, list) and len(pair) == 2:
                        a, b = _number(pair[0]), _number(pair[1])
                        if a is not None and b is not None:
                            self.days.setdefault(str(day), {})[str(mac)] = [a, b]
        cursors = stored.get("cursors")
        if isinstance(cursors, dict):
            for name, value in cursors.items():
                number = _number(value)
                if number is not None:
                    self.cursors[str(name)] = number
        gap = _number(stored.get("gap_seconds_total"))
        if gap is not None:
            self.stats["gap_seconds_total"] = gap


def apply_traffic(
    hosts: list[dict[str, Any]], summary: dict[str, dict[str, Any]] | None
) -> list[dict[str, Any]]:
    """Haengt die Summen an die Geraete (``traffic_week``, ``traffic_week_down``, ...).

    Nur Geraete mit Daten bekommen die Felder; Geraete ohne echte MAC-Adresse
    (VPN-Eintraege) bleiben unberuehrt.
    """
    if not summary:
        return hosts
    for host in hosts:
        if host.get("mac_synthetic"):
            continue
        entry = summary.get(_mac_key(host.get("mac")))
        if not entry:
            continue
        host["traffic_week"] = entry["week"]
        host["traffic_week_down"] = entry["week_down"]
        host["traffic_week_up"] = entry["week_up"]
        host["traffic_today"] = entry["today"]
        host["traffic_days"] = entry["days"]
    return hosts


def status_key(
    enabled: bool,
    error: str | None,
    polled: bool,
    mapped_sources: int,
    devices_with_data: int,
    subsets_mapped: int | None,
) -> str:
    """Zustand der Erfassung fuer den Status-Sensor.

    ``disabled`` (Option aus), ``error`` (Abruf fehlgeschlagen), ``waiting``
    (noch kein Abruf bzw. noch keine Messwerte), ``no_mapping`` (keine
    Datenquelle einem Geraet zugeordnet), ``no_samples`` (Zuordnung da, aber
    keine passenden Messwerte im Abruf) oder ``ok``.
    """
    if not enabled:
        return "disabled"
    if error:
        return "error"
    if not polled:
        return "waiting"
    if mapped_sources <= 0:
        return "no_mapping"
    if devices_with_data > 0:
        return "ok"
    if subsets_mapped is not None and subsets_mapped <= 0:
        return "no_samples"
    return "waiting"
