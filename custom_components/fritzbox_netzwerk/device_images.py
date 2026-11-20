# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 183d3c011066eab5860fa392f98def0db8fd6570d36e7b924935e5c0bd8ac3ba
"""Geraetebilder (2.2.0): Pruefen, Skalieren und Speichern hochgeladener Fotos.

Die Karte skaliert Bilder schon im Browser (Canvas, lange Kante 320 px). Dieses Modul
prueft sie auf dem Server trotzdem noch einmal und bringt sie in dieselbe Form:

* Nur echte Bilder (JPEG, PNG, WebP, GIF, BMP) - kein SVG, kein HTML. Das Format wird aus
  dem Inhalt bestimmt, nicht aus dem Dateinamen oder dem Content-Type der Anfrage.
* Lange Kante hoechstens ``IMAGE_MAX_EDGE``, Ausgabe immer JPEG ohne EXIF-Daten (Ausrichtung
  wird vorher angewendet; Aufnahmeort und Kameradaten bleiben nicht erhalten).
* Eine Obergrenze fuer die Pixelzahl schuetzt vor Dekompressionsbomben.

Ist Pillow nicht installiert (Home Assistant bringt es normalerweise mit), nimmt das Modul
ausschliesslich ein kleines JPEG an, das der Browser bereits skaliert hat.

Keine Home-Assistant-Importe; mit Testdateien pruefbar (blockierend, im Executor aufrufen).
"""
from __future__ import annotations

import io
import os
import re
from typing import Any

MAX_PIXELS = 40_000_000
FALLBACK_MAX_BYTES = 200_000
_MAC_RE = re.compile(r"[0-9a-f]{12}")
_ALLOWED_FORMATS = {"JPEG", "MPO", "PNG", "WEBP", "GIF", "BMP"}


class ImageError(ValueError):
    """Das hochgeladene Bild ist unbrauchbar (Meldung fuer den Nutzer, deutsch)."""


def clean_mac(mac: Any) -> str:
    """MAC-Schluessel (12 Hexzeichen, klein) oder leerer Text."""
    key = "".join(ch for ch in str(mac or "") if ch.isalnum()).lower()
    return key if _MAC_RE.fullmatch(key) else ""


def image_path(directory: str, mac: str) -> str:
    key = clean_mac(mac)
    if not key:
        raise ImageError("Ungueltige MAC-Adresse")
    return os.path.join(directory, f"{key}.jpg")


def version_of(path: str) -> str:
    """Kurze Kennung des Dateistands (aendert sich mit jedem neuen Bild)."""
    stat = os.stat(path)
    return f"{int(stat.st_mtime):x}{stat.st_size:x}"


def normalize_image(data: bytes, max_edge: int) -> bytes:
    """Gibt ein skaliertes JPEG ohne Metadaten zurueck; wirft ``ImageError``."""
    if not data:
        raise ImageError("Leere Datei")
    try:
        from PIL import Image, ImageOps  # noqa: PLC0415 - nur hier gebraucht
    except ImportError:
        if len(data) > FALLBACK_MAX_BYTES or not data.startswith(b"\xff\xd8\xff"):
            raise ImageError(
                "Auf diesem System kann nur ein bereits verkleinertes JPEG angenommen werden"
            ) from None
        return data
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in _ALLOWED_FORMATS:
                raise ImageError("Dateiformat nicht unterstuetzt (erlaubt: JPEG, PNG, WebP, GIF, BMP)")
            width, height = image.size
            if width < 1 or height < 1 or width * height > MAX_PIXELS:
                raise ImageError("Bild zu gross")
            image = ImageOps.exif_transpose(image)
            if image.mode in ("RGBA", "LA", "P"):
                image = image.convert("RGBA")
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")
            image.thumbnail((max_edge, max_edge), Image.LANCZOS)
            out = io.BytesIO()
            image.save(out, format="JPEG", quality=85, optimize=True)
            return out.getvalue()
    except ImageError:
        raise
    except Exception as err:  # noqa: BLE001 - jeder Lesefehler heisst "kein brauchbares Bild"
        raise ImageError("Die Datei ist kein lesbares Bild") from err


def save_image(directory: str, mac: str, data: bytes, max_edge: int) -> str:
    """Speichert das (normalisierte) Bild und gibt die neue Versionskennung zurueck."""
    normalized = normalize_image(data, max_edge)
    path = image_path(directory, mac)
    os.makedirs(directory, exist_ok=True)
    temp = f"{path}.tmp"
    with open(temp, "wb") as handle:
        handle.write(normalized)
    os.replace(temp, path)
    return version_of(path)


def delete_image(directory: str, mac: str) -> bool:
    path = image_path(directory, mac)
    try:
        os.remove(path)
    except FileNotFoundError:
        return False
    return True


def read_image(directory: str, mac: str) -> bytes | None:
    try:
        with open(image_path(directory, mac), "rb") as handle:
            return handle.read()
    except FileNotFoundError:
        return None


def scan_images(directory: str) -> dict[str, str]:
    """Alle vorhandenen Bilder: MAC-Schluessel -> Versionskennung."""
    found: dict[str, str] = {}
    try:
        names = os.listdir(directory)
    except FileNotFoundError:
        return found
    for name in names:
        stem, ext = os.path.splitext(name)
        if ext != ".jpg" or not _MAC_RE.fullmatch(stem):
            continue
        try:
            found[stem] = version_of(os.path.join(directory, name))
        except OSError:
            continue
    return found
