"""Kopiert die mitgelieferten Blueprints in das Home-Assistant-Konfigurationsverzeichnis.

Ohne Home-Assistant-Importe, damit es mit temporären Ordnern prüfbar ist.
Zieht nie ohne ausdrückliche Anforderung etwas an und überschreibt keine
vom Nutzer geänderte Datei, solange ``overwrite`` nicht gesetzt ist.
"""
from __future__ import annotations

import filecmp
import os
import shutil
from typing import Any

DOMAINS = ("automation", "script")
SUBFOLDER = "fritzbox_netzwerk"


def install_blueprints(source_root: str, target_root: str, overwrite: bool = False) -> dict[str, Any]:
    """Kopiert ``<source>/<domain>/fritzbox_netzwerk/*.yaml`` nach ``<target>/<domain>/fritzbox_netzwerk``.

    Rückgabe: ``installiert`` (neu), ``aktualisiert`` (überschrieben, nur mit
    ``overwrite``), ``unveraendert`` (identisch vorhanden) und ``uebersprungen``
    (vorhanden, aber abweichend - z. B. vom Nutzer geändert), jeweils als
    Liste von ``domain/datei``.
    """
    result: dict[str, list[str]] = {
        "installiert": [],
        "aktualisiert": [],
        "unveraendert": [],
        "uebersprungen": [],
    }
    for domain in DOMAINS:
        src_dir = os.path.join(source_root, domain, SUBFOLDER)
        if not os.path.isdir(src_dir):
            continue
        dst_dir = os.path.join(target_root, domain, SUBFOLDER)
        for name in sorted(os.listdir(src_dir)):
            if not name.endswith(".yaml"):
                continue
            src, dst = os.path.join(src_dir, name), os.path.join(dst_dir, name)
            label = f"{domain}/{name}"
            if os.path.exists(dst):
                if filecmp.cmp(src, dst, shallow=False):
                    result["unveraendert"].append(label)
                    continue
                if not overwrite:
                    result["uebersprungen"].append(label)
                    continue
                shutil.copyfile(src, dst)
                result["aktualisiert"].append(label)
                continue
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copyfile(src, dst)
            result["installiert"].append(label)
    return result
