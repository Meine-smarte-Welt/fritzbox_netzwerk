# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): ec83b404f64352ca176cdef1333ad350cf1610b94ee194dd19f5cba18b6378d9
"""HTTP-Zugang fuer Geraetebilder (2.2.0): Abrufen, Hochladen, Entfernen.

``GET    /api/fritzbox_netzwerk/image/<entry_id>/<mac>``  - Bild (jeder angemeldete Nutzer)
``POST   /api/fritzbox_netzwerk/image/<entry_id>/<mac>``  - Bild hochladen (nur Administratoren)
``DELETE /api/fritzbox_netzwerk/image/<entry_id>/<mac>``  - Bild entfernen (nur Administratoren)

Der Rumpf der POST-Anfrage ist das Bild selbst (kein Formular). Die Karte holt Bilder mit
``hass.fetchWithAuth``, weil ein ``<img>``-Element keinen Anmeldekopf senden kann.
"""
from __future__ import annotations

import logging
from http import HTTPStatus

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN, IMAGE_MAX_UPLOAD_BYTES, IMAGE_URL_BASE
from .device_images import ImageError, clean_mac

_LOGGER = logging.getLogger(__name__)


class DeviceImageView(HomeAssistantView):
    """Bild eines Netzwerkgeraets."""

    url = IMAGE_URL_BASE + "/{entry_id}/{mac}"
    name = f"api:{DOMAIN}:image"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    def _coordinator(self, entry_id: str):
        for entry in self._hass.config_entries.async_loaded_entries(DOMAIN):
            if entry.entry_id == entry_id:
                return entry.runtime_data
        return None

    async def get(self, request: web.Request, entry_id: str, mac: str) -> web.Response:
        coordinator = self._coordinator(entry_id)
        key = clean_mac(mac)
        if coordinator is None or not key:
            return web.Response(status=HTTPStatus.NOT_FOUND)
        data = await coordinator.async_read_device_image(key)
        if data is None:
            return web.Response(status=HTTPStatus.NOT_FOUND)
        # Die Adresse der Karte enthaelt die Versionskennung (?v=...), daher darf lange gemerkt werden.
        return web.Response(
            body=data,
            content_type="image/jpeg",
            headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"},
        )

    async def post(self, request: web.Request, entry_id: str, mac: str) -> web.Response:
        if not request["hass_user"].is_admin:
            return web.Response(status=HTTPStatus.UNAUTHORIZED, text="Nur fuer Administratoren")
        coordinator = self._coordinator(entry_id)
        key = clean_mac(mac)
        if coordinator is None or not key:
            return web.Response(status=HTTPStatus.NOT_FOUND)
        length = request.content_length
        if length is not None and length > IMAGE_MAX_UPLOAD_BYTES:
            return web.Response(status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE, text="Bild zu gross")
        data = await request.content.read(IMAGE_MAX_UPLOAD_BYTES + 1)
        if len(data) > IMAGE_MAX_UPLOAD_BYTES:
            return web.Response(status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE, text="Bild zu gross")
        try:
            version = await coordinator.async_set_device_image(key, data)
        except ImageError as err:
            return web.Response(status=HTTPStatus.BAD_REQUEST, text=str(err))
        except OSError as err:
            _LOGGER.warning("Geraetebild konnte nicht gespeichert werden: %s", err)
            return web.Response(status=HTTPStatus.INTERNAL_SERVER_ERROR, text="Speichern fehlgeschlagen")
        return self.json({"image": version})

    async def delete(self, request: web.Request, entry_id: str, mac: str) -> web.Response:
        if not request["hass_user"].is_admin:
            return web.Response(status=HTTPStatus.UNAUTHORIZED, text="Nur fuer Administratoren")
        coordinator = self._coordinator(entry_id)
        key = clean_mac(mac)
        if coordinator is None or not key:
            return web.Response(status=HTTPStatus.NOT_FOUND)
        removed = await coordinator.async_delete_device_image(key)
        return self.json({"removed": bool(removed)})
