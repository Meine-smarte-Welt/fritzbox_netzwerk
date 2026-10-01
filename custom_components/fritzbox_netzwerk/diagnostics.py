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
                # Nur Zaehler - Etiketten und Notizen selbst gehoeren nicht in
                # einen Export (sie koennen Namen und Orte enthalten).
                "notes_count": sum(
                    1 for host in hosts if host.get("label") or host.get("note") or host.get("reserved")
                ),
                "oui_entries": getattr(coordinator, "oui_stats", {}),
                "system_stats_enabled": getattr(coordinator, "system_stats_enabled", False),
                "system_stats_error": getattr(coordinator, "system_stats_error", None),
                "parental_enabled": getattr(coordinator, "parental_enabled", False),
                "profile_reverts_active": len(getattr(coordinator, "profile_reverts", {})),
                "internet_blocks_active": len(getattr(coordinator, "blocked_until", {})),
            },
        },
        TO_REDACT,
    )
