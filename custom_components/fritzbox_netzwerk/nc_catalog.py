# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 7fe9027defaaca4661215b875d1b793f495b1c46d43b7879eaa5b134369b4fc9
"""Meldungsarten für das optionale Notification Center (Schnittstelle Schema 1).

Enthält weder Home-Assistant- noch Netzwerk-Importe und ist ohne laufendes
Home Assistant prüfbar. Der Versand selbst liegt in ``notification_bridge.py``
(in allen Integrationen identisch), die Auslöser im Coordinator.

Gemeldet wird nur, was die Integration ohnehin als Zustandswechsel kennt:

- ``connection_lost``: ein Abruf bei der FRITZ!Box schlägt fehl (derselbe
  Zeitpunkt, an dem die Entitäten „nicht verfügbar“ werden). Löst sich beim
  nächsten gelungenen Abruf.
- ``device_offline``: nur für Geräte, die der Nutzer überwacht, also solche mit
  eigenem „Verbunden“-Status (Repeater und die per IP-Muster ausgewählten
  Netzwerkgeräte). Löst sich, sobald das Gerät wieder aktiv ist.
- ``device_joined``: ein Gerät taucht erstmals im Heimnetz auf (gleicher
  Auslöser wie die Ereignis-Entität „Neues Gerät“). Einmalig.

Es gibt keine neuen Schwellen und keine zusätzlichen Abfragen an die Box.
"""
from __future__ import annotations

from typing import Any

NC_TYPE_CONNECTION_LOST = "connection_lost"
NC_TYPE_DEVICE_OFFLINE = "device_offline"
NC_TYPE_DEVICE_JOINED = "device_joined"

# Reihenfolge nach Dringlichkeit (warning vor info), dann wie im Katalog.
NC_TYPE_ORDER: tuple[str, ...] = (
    NC_TYPE_CONNECTION_LOST,
    NC_TYPE_DEVICE_OFFLINE,
    NC_TYPE_DEVICE_JOINED,
)

NC_NAME = "FRITZ!Box Netzwerk"
NC_ICON = "mdi:router-network"
NC_CONNECTION_KEY = "fritzbox"

NC_CATALOG: list[dict[str, Any]] = [
    {
        "type": NC_TYPE_CONNECTION_LOST,
        "severity": "warning",
        "resolvable": True,
        "enabled_default": True,
        "icon": "mdi:lan-disconnect",
        "texts": {
            "de": {
                "label": "Verbindung zur FRITZ!Box verloren",
                "title": "FRITZ!Box nicht erreichbar",
                "message": "Die Verbindung zur FRITZ!Box ist unterbrochen. Home Assistant versucht es automatisch erneut.",
            },
            "en": {
                "label": "Connection to FRITZ!Box lost",
                "title": "FRITZ!Box not reachable",
                "message": "The connection to the FRITZ!Box is interrupted. Home Assistant retries automatically.",
            },
            "nl": {
                "label": "Verbinding met FRITZ!Box verbroken",
                "title": "FRITZ!Box niet bereikbaar",
                "message": "De verbinding met de FRITZ!Box is verbroken. Home Assistant probeert het automatisch opnieuw.",
            },
            "fr": {
                "label": "Connexion à la FRITZ!Box perdue",
                "title": "FRITZ!Box injoignable",
                "message": "La connexion à la FRITZ!Box est interrompue. Home Assistant réessaie automatiquement.",
            },
            "es": {
                "label": "Conexión con la FRITZ!Box perdida",
                "title": "FRITZ!Box no accesible",
                "message": "Se ha interrumpido la conexión con la FRITZ!Box. Home Assistant lo reintenta automáticamente.",
            },
        },
    },
    {
        "type": NC_TYPE_DEVICE_OFFLINE,
        "severity": "info",
        "resolvable": True,
        "enabled_default": True,
        "icon": "mdi:wifi-off",
        "texts": {
            "de": {
                "label": "Überwachtes Gerät offline",
                "title": "{name} ist offline",
                "message": "{name} ist im Heimnetz nicht mehr aktiv.",
            },
            "en": {
                "label": "Monitored device offline",
                "title": "{name} is offline",
                "message": "{name} is no longer active on the home network.",
            },
            "nl": {
                "label": "Bewaakt apparaat offline",
                "title": "{name} is offline",
                "message": "{name} is niet meer actief in het thuisnetwerk.",
            },
            "fr": {
                "label": "Appareil surveillé hors ligne",
                "title": "{name} est hors ligne",
                "message": "{name} n'est plus actif sur le réseau domestique.",
            },
            "es": {
                "label": "Dispositivo supervisado sin conexión",
                "title": "{name} está sin conexión",
                "message": "{name} ya no está activo en la red doméstica.",
            },
        },
    },
    {
        "type": NC_TYPE_DEVICE_JOINED,
        "severity": "info",
        "resolvable": False,
        "enabled_default": True,
        "icon": "mdi:devices",
        "texts": {
            "de": {
                "label": "Neues Gerät im Netz",
                "title": "Neues Gerät: {name}",
                "message": "{name} ({ip}) ist zum ersten Mal im Heimnetz aufgetaucht.",
            },
            "en": {
                "label": "New device on the network",
                "title": "New device: {name}",
                "message": "{name} ({ip}) appeared on the home network for the first time.",
            },
            "nl": {
                "label": "Nieuw apparaat in het netwerk",
                "title": "Nieuw apparaat: {name}",
                "message": "{name} ({ip}) is voor het eerst in het thuisnetwerk verschenen.",
            },
            "fr": {
                "label": "Nouvel appareil sur le réseau",
                "title": "Nouvel appareil : {name}",
                "message": "{name} ({ip}) est apparu pour la première fois sur le réseau domestique.",
            },
            "es": {
                "label": "Nuevo dispositivo en la red",
                "title": "Nuevo dispositivo: {name}",
                "message": "{name} ({ip}) ha aparecido por primera vez en la red doméstica.",
            },
        },
    },
]


def _mac_key(mac: Any) -> str:
    """Vergleichsschlüssel einer MAC-Adresse (wie ``hosts.mac_key``)."""
    if not mac:
        return ""
    return "".join(ch for ch in str(mac) if ch.isalnum()).lower()


def display_name(host: dict[str, Any]) -> str:
    """Anzeigename für Meldungstexte: Name, sonst IP, sonst MAC-Adresse."""
    return str(host.get("name") or host.get("ip") or host.get("mac") or "?")


def device_subject(host: dict[str, Any]) -> dict[str, Any]:
    """``subject`` einer Geräte-Meldung (immer mitsenden, siehe Schnittstelle)."""
    return {"id": _mac_key(host.get("mac")), "name": display_name(host), "kind": "device"}


def joined_placeholders(host: dict[str, Any]) -> dict[str, str]:
    """Platzhalter für „Neues Gerät“ - nur Name und IP, keine weiteren Angaben."""
    return {"name": display_name(host), "ip": str(host.get("ip") or "–")}


def offline_items(
    hosts: list[dict[str, Any]], monitored: set[str]
) -> dict[str, dict[str, Any]]:
    """Aktuell offline gemeldete, überwachte Geräte (Schlüssel = MAC-Schlüssel).

    Ein überwachtes Gerät, das gar nicht (mehr) in der Geräteliste steht, gilt
    nicht als offline - wie beim „Verbunden“-Status, der dann „unbekannt“ ist.
    """
    items: dict[str, dict[str, Any]] = {}
    for host in hosts:
        key = _mac_key(host.get("mac"))
        if not key or key not in monitored or host.get("active"):
            continue
        items[key] = {
            "key": key,
            "subject": device_subject(host),
            "placeholders": {"name": display_name(host)},
        }
    return items


def diff_offline(
    previous: set[str], current: dict[str, dict[str, Any]]
) -> tuple[list[str], list[str]]:
    """Zustandswechsel: (neu offline, nicht mehr offline), stabil sortiert."""
    now = set(current)
    return sorted(now - previous), sorted(previous - now)
