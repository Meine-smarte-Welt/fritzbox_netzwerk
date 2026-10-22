# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): f47068550997c87cabe2b82d12d76b954fbf8f7980864e691de2c869ab49fcf7
"""Diagnose-Export fuer fritzbox_netzwerk (Idee 15 aus feature-ideen.md).

Liefert die Angaben, die zur Fehlersuche bei einer GitHub-Issue-Meldung am
haeufigsten gebraucht werden (Konfiguration ohne Zugangsdaten, Verbindungs-
und WLAN-Status, Zusammenfassung der Geraeteliste), OHNE personenbezogene
oder sicherheitsrelevante Daten: MAC-/IP-Adressen, Geraetenamen und
Zugangsdaten werden geschwaerzt. Genau diese Angaben mussten bei mehreren
in 1.6.2 behobenen Fehlern (401 bei bestimmten Boxen, Mesh-Repeater-
Erkennung) erst muehsam per Rueckfrage im Issue erfragt werden.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import VERSION

# Konfigurationsfelder, die nie im Klartext in einem Diagnose-Export landen
# duerfen. CONF_HOST wird mitgeschwaerzt, weil er bei aktivem Fernzugriff
# (seit 1.6.2) ein oeffentlicher MyFRITZ!/DynDNS-Name sein kann.
TO_REDACT_CONFIG = {CONF_HOST, CONF_USERNAME, CONF_PASSWORD}

# Felder je Netzwerkgeraet (siehe hosts.normalize_host), die personenbezogen
# sind oder das Heimnetz konkret identifizierbar machen. async_redact_data
# ersetzt jedes Vorkommen dieser Schluessel rekursiv, unabhaengig von der
# Verschachtelungstiefe - trifft also sowohl auf "hosts" als auch auf
# "mesh" in der Coordinator-Momentaufnahme zu.
TO_REDACT_HOST_FIELDS = {
    "mac",
    "ip",
    "name",
    "host_name",
    "friendly_name",
    "ha_name",
    "ha_device_id",
    "ha_area",
}

# "connection" (siehe coordinator._async_update_data) enthaelt die externe
# IPv4-Adresse der Box - das verraet indirekt den ungefaehren Wohnort.
TO_REDACT_CONNECTION_FIELDS = {"external_ip"}

TO_REDACT = TO_REDACT_CONFIG | TO_REDACT_HOST_FIELDS | TO_REDACT_CONNECTION_FIELDS


def _nc_diagnostics(coordinator: Any) -> dict[str, Any]:
    """Schalterstand und Zaehler der gesendeten Meldungen (ohne Inhalte)."""
    nc = getattr(coordinator, "nc", None)
    if nc is None:
        return {}
    snapshot = nc.snapshot()
    return {
        "detected": snapshot["available"],
        "enabled": snapshot["enabled"],
        "types": {item["type"]: item["enabled"] for item in snapshot["types"]},
        "sent": dict(getattr(coordinator, "nc_counts", {}) or {}),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Baut den Diagnose-Export fuer einen Konfigurationseintrag."""
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    hosts = data.get("hosts", [])

    return async_redact_data(
        {
            "integration_version": VERSION,
            "entry": {
                "data": dict(entry.data),
                "options": dict(entry.options),
            },
            "coordinator": {
                "last_scan": data.get("last_scan"),
                "track_address_source": data.get("track_address_source"),
                "summary": data.get("summary"),
                "connection": data.get("connection"),
                "wlan": data.get("wlan"),
                "mesh": data.get("mesh"),
                # Nur die Felder, die fuer die Fehlersuche typischerweise
                # noetig sind (Verbindungsart, Modell, Flags) - der Rest
                # (Name/IP/MAC) ist ohnehin geschwaerzt, wird aber bewusst
                # nicht mitgeschickt, um den Export kurz zu halten.
                "hosts": [
                    {
                        key: host.get(key)
                        for key in (
                            "mac",
                            "ip",
                            "active",
                            "connection",
                            "band",
                            "ip_class",
                            "guest",
                            "blocked",
                            "update_available",
                            "model",
                            "repeater",
                            "meshable",
                            "vendor",
                            "mac_random",
                            "wan_access",
                        )
                    }
                    for host in hosts
                ],
                "host_count": len(hosts),
                # Zur Fehlersuche (z. B. "Geraete fehlen"): wie viele Eintraege die
                # Box lieferte und wie die Mesh-/Gast-Erkennung entschied.
                "hosts_active": sum(1 for host in hosts if host.get("active")),
                "hosts_inactive": sum(1 for host in hosts if not host.get("active")),
                "mesh_repeaters_from_topology": len(getattr(coordinator, "_mesh_repeaters", {}) or {}),
                "guest_wlan_service": getattr(coordinator, "_guest_service", None),
                # Issue #20: von Hand gewaehlter Dienst (0 = automatisch) und
                # das Band, das jeder WLAN-Dienst der Box meldete ("" = keins).
                "guest_wlan_service_configured": getattr(
                    coordinator, "configured_guest_service", 0
                ),
                "wlan_service_bands": {
                    str(index): band
                    for index, band in (getattr(coordinator, "_guest_bands", {}) or {}).items()
                },
                # Issue #24: was die Box lieferte, bevor die Integration
                # Eintraege ohne MAC-Adresse verwarf (Abgleich mit host_count).
                "box_hosts": dict(getattr(coordinator, "_host_stats", {}) or {}),
                # Issue #31: ob und woher die Reservierungen ("immer die gleiche
                # IPv4-Adresse") der Box gelesen wurden - nur Zaehler und Quelle.
                "reservations": {
                    **dict(getattr(coordinator, "reservation_info", {}) or {}),
                    "error": getattr(coordinator, "reservation_error", None),
                },
                # Nur Zaehler - Etiketten und Notizen selbst gehoeren nicht in
                # einen Export (sie koennen Namen und Orte enthalten).
                "notes_count": sum(
                    1 for host in hosts if host.get("label") or host.get("note") or host.get("reserved")
                ),
                "oui_entries": getattr(coordinator, "oui_stats", {}),
                "traffic": getattr(coordinator, "traffic_diagnostics", {}),
                "system_stats_enabled": getattr(coordinator, "system_stats_enabled", False),
                "system_stats_error": getattr(coordinator, "system_stats_error", None),
                "parental_enabled": getattr(coordinator, "parental_enabled", False),
                "profile_reverts_active": len(getattr(coordinator, "profile_reverts", {})),
                "internet_blocks_active": len(getattr(coordinator, "blocked_until", {})),
                # Notification Center: nur Schalterstand und Zaehler je Meldungsart,
                # keine Namen, MAC-Adressen oder Texte.
                "notification_center": _nc_diagnostics(coordinator),
            },
        },
        TO_REDACT,
    )
