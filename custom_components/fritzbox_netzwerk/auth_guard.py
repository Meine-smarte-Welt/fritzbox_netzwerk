"""Schutz vor voreiligen Neu-Anmeldungen (ohne Abhaengigkeit von Home Assistant).

Die FRITZ!Box lehnt Anmeldungen gelegentlich kurzzeitig ab (HTTP 401 bzw.
UPnP 606), obwohl Benutzername und Kennwort stimmen - etwa waehrend eines
Neustarts oder Updates, bei mehreren gleichzeitigen Anmeldungen oder wenn sie
nach schnell aufeinanderfolgenden Anmeldungen eine Wartezeit verhaengt.

Bis 1.7.0 loeste schon EIN solcher Fehler die Meldung "Neu authentifizieren"
in Home Assistant aus. Seit 1.7.1 zaehlt dieser Waechter aufeinanderfolgende
Fehlschlaege je Konfigurationseintrag: erst nach ``AUTH_FAILURE_LIMIT``
Fehlschlaegen in Folge gilt die Anmeldung als wirklich abgelehnt. Ein
erfolgreicher Abruf setzt den Zaehler zurueck.
"""

from __future__ import annotations

from typing import Final

# Anzahl aufeinanderfolgender abgelehnter Anmeldungen, ab der die erneute
# Anmeldung verlangt wird. Bei 60 s Abfrageintervall sind das rund 3 Minuten;
# beim Start liegen dazwischen die Wiederholungen von Home Assistant.
AUTH_FAILURE_LIMIT: Final = 3


class AuthFailureGuard:
    """Zaehlt aufeinanderfolgende Anmeldefehler je Schluessel (Entry-ID)."""

    def __init__(self, limit: int = AUTH_FAILURE_LIMIT) -> None:
        """Legt den Waechter an."""
        self._limit = limit
        self._failures: dict[str, int] = {}

    def failure(self, key: str) -> tuple[int, bool]:
        """Merkt einen abgelehnten Abruf.

        Liefert ``(Anzahl, erreicht)``. Ist das Limit erreicht, wird der Zaehler
        zurueckgesetzt: nach der erneuten Anmeldung (die die Integration neu
        laedt) beginnt die Zaehlung von vorn und ein einzelner weiterer Fehler
        verlangt nicht sofort wieder eine Anmeldung.
        """
        count = self._failures.get(key, 0) + 1
        if count >= self._limit:
            self._failures.pop(key, None)
            return count, True
        self._failures[key] = count
        return count, False

    def success(self, key: str) -> None:
        """Setzt den Zaehler nach einem erfolgreichen Abruf zurueck."""
        self._failures.pop(key, None)

    def count(self, key: str) -> int:
        """Aktueller Stand (fuer Diagnose und Tests)."""
        return self._failures.get(key, 0)
