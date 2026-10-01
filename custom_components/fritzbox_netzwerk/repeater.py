"""Gemeinsame Bausteine fuer Repeater als eigene Home-Assistant-Geraete.

AVM-Repeater im Mesh tauchen in der Hostliste der FRITZ!Box als ganz normale
Netzwerkgeraete auf (erkennbar am Modell, siehe ``hosts.is_repeater``). Wer
moechte, bekommt sie zusaetzlich als eigenes Home-Assistant-Geraet - mit
Verbunden-Status (``binary_sensor.py``) und, bei aktivierter Steuerung, mit
einem Neustart-Button (``button.py``). Dieses Modul haelt, was beide
Plattformen teilen.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    CONF_ENABLE_HOST_DEVICES,
    CONF_ENABLE_REPEATERS,
    CONF_HOST_DEVICE_FILTER,
    DEFAULT_ENABLE_HOST_DEVICES,
    DEFAULT_ENABLE_REPEATERS,
    DEFAULT_HOST_DEVICE_FILTER,
    DOMAIN,
)
from .hosts import host_device_selection, mac_key

if TYPE_CHECKING:
    from . import FritzboxNetzwerkConfigEntry

REPEATER_MANUFACTURER = "AVM"


def repeaters_enabled(entry: FritzboxNetzwerkConfigEntry) -> bool:
    """Ob Repeater als eigene Geraete angelegt werden sollen."""
    return bool(entry.options.get(CONF_ENABLE_REPEATERS, DEFAULT_ENABLE_REPEATERS))


def repeater_hosts(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Alle Repeater aus den Coordinator-Daten (nur mit gueltiger MAC)."""
    return [
        host
        for host in (data or {}).get("hosts", [])
        if host.get("repeater") and mac_key(host.get("mac"))
    ]


def find_repeater(data: dict[str, Any] | None, key: str) -> dict[str, Any] | None:
    """Sucht einen Repeater ueber seinen MAC-Schluessel."""
    for host in repeater_hosts(data):
        if mac_key(host.get("mac")) == key:
            return host
    return None


def repeater_identifier(entry: FritzboxNetzwerkConfigEntry, key: str) -> str:
    """Stabile Kennung des Repeater-Geraets (haengt an der MAC-Adresse)."""
    return f"{entry.entry_id}_repeater_{key}"


def _via_device(
    hass: HomeAssistant, entry: FritzboxNetzwerkConfigEntry
) -> dict[str, Any]:
    """Verweis auf die Haupt-FRITZ!Box - versionsuebergreifend.

    Neuere Home-Assistant-Staende kennen ``via_device`` (ueber die
    Identifier) nur noch als veraltet und wollen ``via_device_id``; aeltere
    kennen ausschliesslich ``via_device``. Ob ``DeviceInfo`` das neue Feld
    fuehrt, laesst sich zur Laufzeit an seinen Annotationen ablesen.
    """
    main = (DOMAIN, entry.entry_id)
    if "via_device_id" not in DeviceInfo.__annotations__:
        return {"via_device": main}
    registry = dr.async_get(hass)
    finder = getattr(registry, "async_get_device_by_identifier", None)
    device = (
        finder(main, entry.entry_id)
        if finder is not None
        else registry.async_get_device(identifiers={main})
    )
    return {"via_device_id": device.id} if device else {}


def repeater_device_info(
    hass: HomeAssistant,
    entry: FritzboxNetzwerkConfigEntry,
    host: dict[str, Any],
) -> DeviceInfo:
    """Beschreibt den Repeater als Geraet, angehaengt an die FRITZ!Box."""
    key = mac_key(host["mac"])
    url = str(host.get("url") or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        url = f"http://{host['ip']}" if host.get("ip") else ""
    info = DeviceInfo(
        identifiers={(DOMAIN, repeater_identifier(entry, key))},
        connections={(dr.CONNECTION_NETWORK_MAC, host["mac"])},
        manufacturer=REPEATER_MANUFACTURER,
        model=host.get("model") or None,
        name=host.get("name") or host["mac"],
    )
    if url:
        info["configuration_url"] = url
    info.update(_via_device(hass, entry))  # type: ignore[typeddict-item]
    return info


# ---------------------------------------------------------------------------
# Netzwerkgeraete als Home-Assistant-Geraete (Idee 9 aus feature-ideen.md)
# ---------------------------------------------------------------------------

# Obergrenze: jedes Geraet bekommt ein HA-Geraet und eine Entitaet. Bei einem
# zu weit gefassten Muster ("*" in einem grossen Netz) soll das Entitaets-
# register nicht unbemerkt mit Hunderten Eintraegen volllaufen.
MAX_HOST_DEVICES = 150


def host_devices_enabled(entry: FritzboxNetzwerkConfigEntry) -> bool:
    """Ob Netzwerkgeraete als eigene Geraete angelegt werden sollen."""
    return bool(entry.options.get(CONF_ENABLE_HOST_DEVICES, DEFAULT_ENABLE_HOST_DEVICES))


def selected_host_devices(
    entry: FritzboxNetzwerkConfigEntry, data: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Die Geraete, die laut Auswahlmuster ein eigenes HA-Geraet bekommen."""
    if not host_devices_enabled(entry):
        return []
    pattern = entry.options.get(CONF_HOST_DEVICE_FILTER, DEFAULT_HOST_DEVICE_FILTER)
    return host_device_selection((data or {}).get("hosts", []), pattern)


def host_identifier(entry: FritzboxNetzwerkConfigEntry, key: str) -> str:
    """Stabile Kennung des Geraets (haengt an der MAC-Adresse)."""
    return f"{entry.entry_id}_host_{key}"


def host_device_info(
    hass: HomeAssistant,
    entry: FritzboxNetzwerkConfigEntry,
    host: dict[str, Any],
) -> DeviceInfo:
    """Beschreibt ein Netzwerkgeraet als HA-Geraet, angehaengt an die FRITZ!Box.

    Als Hersteller dient der Name aus der OUI-Liste (leer bei zufaelliger oder
    unbekannter MAC). Die Weboberflaeche wird nur verlinkt, wenn die Box eine
    eigene Adresse dafuer meldet - eine geratene ``http://<IP>`` waere bei
    vielen Smart-Home-Geraeten falsch.
    """
    key = mac_key(host["mac"])
    info = DeviceInfo(
        identifiers={(DOMAIN, host_identifier(entry, key))},
        connections={(dr.CONNECTION_NETWORK_MAC, host["mac"])},
        manufacturer=host.get("vendor") or None,
        model=host.get("model") or None,
        name=host.get("name") or host["mac"],
    )
    url = str(host.get("url") or "").strip()
    if url.lower().startswith(("http://", "https://")):
        info["configuration_url"] = url
    info.update(_via_device(hass, entry))  # type: ignore[typeddict-item]
    return info
