"""Versionsvergleich und Auswertung der GitHub-Release-Antwort.

Enthält weder Home-Assistant- noch Netzwerk-Importe und ist ohne laufendes
Home Assistant prüfbar. Der eigentliche Abruf (HTTP) liegt im Coordinator.
"""
from __future__ import annotations

import re
from typing import Any

# 1.7.0, v1.7.0, 1.7.0b2, 1.7.0-beta.2, 1.7.0rc1
_VERSION_RE = re.compile(
    r"^v?(\d+)\.(\d+)(?:\.(\d+))?(?:[-.]?(a|alpha|b|beta|rc)[-.]?(\d+)?)?$", re.IGNORECASE
)
_PRE_ORDER = {"a": 0, "alpha": 0, "b": 1, "beta": 1, "rc": 2}
RELEASE_URL_PREFIX = "https://github.com/"


def parse_version(text: Any) -> tuple[int, int, int, int, int] | None:
    """Zerlegt eine Versionsnummer in einen vergleichbaren Tupel.

    Vorabversionen sind kleiner als die fertige Version
    (``1.7.0b2 < 1.7.0``); unlesbare Angaben liefern ``None``.
    """
    match = _VERSION_RE.match(str(text or "").strip())
    if not match:
        return None
    major, minor, patch, pre, pre_no = match.groups()
    if pre is None:
        stage, number = 3, 0  # fertige Version steht über allen Vorabversionen
    else:
        stage, number = _PRE_ORDER[pre.lower()], int(pre_no or 0)
    return int(major), int(minor), int(patch or 0), stage, number


def is_newer(latest: Any, installed: Any) -> bool:
    """Ob ``latest`` neuer als ``installed`` ist (unlesbar = ``False``)."""
    new, old = parse_version(latest), parse_version(installed)
    return new is not None and old is not None and new > old


def parse_release(payload: Any) -> dict[str, str] | None:
    """Liest ``version`` und ``url`` aus der Antwort von ``releases/latest``.

    Entwürfe und Vorabversionen werden ignoriert; die URL wird nur
    übernommen, wenn sie auf github.com zeigt (sie landet als Link in der Karte).
    """
    if not isinstance(payload, dict) or payload.get("draft") or payload.get("prerelease"):
        return None
    tag = str(payload.get("tag_name") or "").strip()
    if parse_version(tag) is None:
        return None
    url = str(payload.get("html_url") or "")
    if not url.startswith(RELEASE_URL_PREFIX):
        url = ""
    return {"version": tag.lstrip("vV"), "url": url}


def build_version_info(installed: str, release: dict[str, str] | None, checked: str | None) -> dict[str, Any]:
    """Baut das Attribut ``version`` für Sensor und Karte."""
    latest = (release or {}).get("version")
    return {
        "installed": installed,
        "latest": latest,
        "update_available": bool(latest and is_newer(latest, installed)),
        "release_url": (release or {}).get("url") or "",
        "checked": checked,
    }
