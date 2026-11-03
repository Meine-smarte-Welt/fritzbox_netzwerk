# Experimentelle Funktionen – FRITZ!Box Netzwerk

Stand: 2026-11-03 · Version: 2.1.2

Diese Funktionen sind **ungeprüft**: Sie wurden nur gegen nachgebaute Daten getestet, nicht an einer echten FRITZ!Box. Bestätigt Thorsten eine Funktion, wandert sie in die Historie unten.

**Hinweis zum Stand:** Einen Hauptschalter „Experimentelle Funktionen anzeigen“ gibt es in dieser Integration noch nicht. Die Funktionen sind deshalb sichtbar bzw. aktiv, aber ausdrücklich ungeprüft.

**Seit 2.1.2:** Die Kaskaden-Erkennung ist die erste Funktion mit eigener Option (Standard aus). Die übrigen sind unverändert sichtbar bzw. aktiv.

## Offen (noch zu prüfen)

| Funktion | Seit | Warum experimentell | Was zu prüfen ist | Status |
|---|---|---|---|---|
| Kaskadierte FRITZ!Boxen als Zwischenstation in der Mesh-Karte (Issue #41), Option „Kaskadierte FRITZ!Boxen als Zwischenstation erkennen (experimentell)“ (`enable_cascade_detection`, Standard aus) | 2.1.1 (Option seit 2.1.2) | Nur gegen eine nachgebaute Topologie geprüft; in 2.1.1 galt die Regel immer und stufte jede per Kabel angeschlossene FRITZ!Box als Switch ein, auch reine Endgeräte | 1. Option einschalten, Home Assistant lädt die Integration neu · 2. Zwei bis drei FRITZ!Boxen per Kabel hintereinander (Router-Betrieb) · 3. Mesh-Karte öffnen · 4. Erwartet: Kette Box → Box → Box mit Router-Symbol, Endgeräte an der richtigen Box; eine FRITZ!Box, die nur Endgerät ist, erscheint nicht als Switch · 5. Option aus: Verhalten wie 2.1.0 | offen |
| Switch-Erkennung in der Mesh-Karte (Issue #37) | 2.1.0 | Heuristik, nicht an echter Box geprüft; seit 2.1.2 wieder wie in 2.1.0 (ohne die Kaskaden-Option) | Switch im Heimnetz mit Geräten dahinter · Erwartet: Eintrag „Switch“ in der Kette, nicht in den Online-Zahlen | offen |
| Wiederverwendung der Web-Sitzung (Issue #35) | 2.1.0 | Nur gegen simulierten Server geprüft; Ursache der Mails ungeklärt | Optionale Web-Funktionen einschalten, Abfrageintervall kurz · FRITZ!Box-Ereignisse zählen · Erwartet: deutlich weniger „Anmeldung an der Benutzeroberfläche“ | offen |
| Sensor „Externe IPv6“ (Issue #36) | 2.1.0 | Nicht an echter Box geprüft | Box mit IPv6 · Sensor und Attribute `prefix`, `prefix_length` ansehen | offen |
| IP ändern (Issue #38) | 2.1.0 | Nicht an echter Box geprüft | Gerät mit fester IP · „Ändern“ · neue IP wird übernommen | offen |
| „Alle ungenutzten Verbindungen entfernen“ (Dienst `remove_unused_connections`) | 2.0.2 | Weboberflächen-Schnittstelle (FRITZ!OS 8) nur im Browser beobachtet, Anfrage nie abgesendet | Testbox mit alten Einträgen · Aufräumen starten · Erwartet: nur unbenutzte Verbindungen verschwinden | offen |
| Statische IP setzen (Dienst `set_static_ip`) | 1.8.0 | Undokumentierte Weboberfläche, nach Beschreibung eines Drittprojekts, an keiner Box geprüft | Gerät ohne feste IP · IP festlegen · in der FRITZ!Box-Oberfläche prüfen | offen |
| VPN-Gegenstellen ohne MAC (Kennung `VPN:<IP>`, Issue #29) | 2.0.0 | Unbekannt, ob die Box WireGuard-Gegenstellen so meldet | Box mit WireGuard-Gegenstelle · Diagnose `box_hosts.without_mac_samples` ansehen · Eintrag erscheint in Liste und Zählern | offen |
| MAC-Filter / Pairing | 1.x | Laut README experimentell, nur mit laufendem Home Assistant abgesichert | Pairing starten und beenden · MAC-Filter schaltet wieder wie vorher | offen |


## Geprüft (Historie)

Noch keine Eintragung seit Einführung dieser Datei.
