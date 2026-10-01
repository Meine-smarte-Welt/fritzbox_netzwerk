#!/usr/bin/env python3
"""Baut custom_components/fritzbox_netzwerk/data/oui.txt aus den drei
offiziellen IEEE-Herstellerregistern neu auf: MA-L ("OUI", 24 Bit, grosse
Hersteller), MA-M (28 Bit) und MA-S (36 Bit, beide fuer kleinere Hersteller
mit weniger benoetigten Adressen - siehe Idee 4a in feature-ideen.md: genau
die Smart-Home-Hersteller, die bisher oft als "unbekannt" erschienen).

WICHTIG: Dieses Sandbox-Projekt hat selbst KEINEN Netzwerkzugriff auf
standards-oui.ieee.org (von der Betriebsumgebung blockiert) - das Skript
wurde deshalb nur gegen eine kleine, selbst gebaute Beispiel-CSV getestet
(siehe tests/test_update_oui.py), NICHT gegen die echten IEEE-Dateien. Bitte
einmal mit --limit 20 testweise laufen lassen und das Ergebnis stichprobenartig
pruefen, bevor die komplette Liste eingecheckt wird.

Die Download-URLs unten sind die zum Zeitpunkt der Erstellung (2026)
dokumentierten CSV-Exporte. Falls einer davon 404 liefert: aktuelle URLs
auf https://standards.ieee.org/products-programs/regauth/ nachschlagen und
per --oui-url/--mam-url/--oui36-url ersetzen.

Format jeder IEEE-CSV (gleich fuer alle drei Register):
    Registry,Assignment,Organization Name,Organization Address
    MA-L,000000,XEROX CORPORATION,"..."

Aufruf:
    python3 scripts/update_oui.py
    python3 scripts/update_oui.py --limit 20   # nur zum Ausprobieren
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import urllib.request
from pathlib import Path

DEFAULT_OUI_URL = "https://standards-oui.ieee.org/oui/oui.csv"
DEFAULT_MAM_URL = "https://standards-oui.ieee.org/oui28/mam.csv"
DEFAULT_OUI36_URL = "https://standards-oui.ieee.org/oui36/oui36.csv"

OUTPUT_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components/fritzbox_netzwerk/data/oui.txt"
)

_HEX_RE = re.compile(r"^[0-9A-Fa-f]+$")

# Siehe hosts.UNRESOLVED_OWNERS: Eintraege, die selbst nur auf ein kleineres
# Register verweisen, sind keine Auskunft ueber den Hersteller.
UNRESOLVED_OWNERS = {"ieee registration authority"}


def fetch_csv(url: str, timeout: int = 60) -> str:
    """Laedt eine der drei IEEE-CSV-Dateien (blockierend)."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "fritzbox_netzwerk-update_oui/1.0"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read().decode("utf-8", errors="replace")


def parse_registry_csv(text: str) -> dict[str, str]:
    """Liest eine IEEE-Registry-CSV (MA-L/MA-M/MA-S, alle im gleichen Format).

    Erwartete Spalten (Gross-/Kleinschreibung und Reihenfolge wird toleriert):
    "Assignment" (das Hex-Praefix, 6/7/9 Zeichen je nach Register) und
    "Organization Name". Andere Spalten werden ignoriert.
    """
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return {}
    columns = {name.strip().lower(): name for name in reader.fieldnames}
    assignment_col = columns.get("assignment")
    name_col = columns.get("organization name")
    if not assignment_col or not name_col:
        raise ValueError(
            f"Unerwartete CSV-Kopfzeile, erwartet u. a. 'Assignment' und "
            f"'Organization Name': {reader.fieldnames}"
        )

    table: dict[str, str] = {}
    for row in reader:
        prefix = (row.get(assignment_col) or "").strip().upper()
        name = " ".join((row.get(name_col) or "").split())
        if not prefix or not name or not _HEX_RE.fullmatch(prefix):
            continue
        if name.lower() in UNRESOLVED_OWNERS:
            continue
        table[prefix] = name
    return table


def build_table(
    oui_text: str, mam_text: str, oui36_text: str, limit: int | None = None
) -> dict[str, str]:
    """Merged die drei Register. Spaetere Aufrufe ueberschreiben bei Konflikt -
    kommt praktisch nicht vor, da die Praefix-Laengen unterschiedlich sind."""
    table: dict[str, str] = {}
    for text in (oui_text, mam_text, oui36_text):
        table.update(parse_registry_csv(text))
    if limit:
        table = dict(list(table.items())[:limit])
    return table


def write_oui_txt(table: dict[str, str], path: Path) -> None:
    lines = [
        "# FRITZ!Box Netzwerk - Hersteller-Zuordnung (OUI) fuer MAC-Adressen",
        "# Format: PRAEFIX:Herstellername  (PRAEFIX = 6 Hex-Zeichen fuer MA-L,",
        "#         7 fuer MA-M, 9 fuer MA-S - siehe hosts.OUI_PREFIX_LENGTHS)",
        "# Quelle: IEEE Registration Authority, MA-L/MA-M/MA-S-Register.",
        "# Erzeugt von scripts/update_oui.py - nicht von Hand bearbeiten,",
        "# eigene Zuordnungen gehoeren in eine separate Datei (siehe README).",
        f"# Eintraege: {len(table)}",
    ]
    for prefix in sorted(table):
        lines.append(f"{prefix}:{table[prefix]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oui-url", default=DEFAULT_OUI_URL)
    parser.add_argument("--mam-url", default=DEFAULT_MAM_URL)
    parser.add_argument("--oui36-url", default=DEFAULT_OUI36_URL)
    parser.add_argument(
        "--limit", type=int, default=None, help="Nur die ersten N Einträge schreiben (zum Testen)"
    )
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args(argv)

    print(f"Lade MA-L von {args.oui_url} ...", file=sys.stderr)
    oui_text = fetch_csv(args.oui_url)
    print(f"Lade MA-M von {args.mam_url} ...", file=sys.stderr)
    mam_text = fetch_csv(args.mam_url)
    print(f"Lade MA-S von {args.oui36_url} ...", file=sys.stderr)
    oui36_text = fetch_csv(args.oui36_url)

    table = build_table(oui_text, mam_text, oui36_text, limit=args.limit)
    write_oui_txt(table, args.output)
    print(f"{len(table)} Einträge in {args.output} geschrieben.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
