# Experimentelle Funktionen – FRITZ!Box Netzwerk

Stand: 2026-11-03 · Version: 2.1.1

Diese Funktionen sind **ungeprüft**: Sie wurden nur gegen nachgebaute Daten getestet, nicht an einer echten FRITZ!Box. Bestätigt Thorsten eine Funktion, wandert sie in die Historie unten.

**Hinweis zum Stand:** Einen Hauptschalter „Experimentelle Funktionen anzeigen“ gibt es in dieser Integration noch nicht. Die Funktionen sind deshalb sichtbar bzw. aktiv, aber ausdrücklich ungeprüft.

## Offen (noch zu prüfen)

| Funktion | Seit | Warum experimentell | Was zu prüfen ist | Status |
|---|---|---|---|---|
| Kaskadierte FRITZ!Boxen als Zwischenstation in der Mesh-Karte (Issue #41) | 2.1.1 | Nur gegen eine nachgebaute Topologie geprüft; der Screenshot aus dem Issue war nicht einsehbar | 1. Zwei bis drei FRITZ!Boxen per Kabel hintereinander (Router-Betrieb) · 2. Mesh-Karte öffnen · 3. Erwartet: Kette Box → Box → Box mit Router-Symbol, Endgeräte an der richtigen Box | offen |
| Switch-Erkennung in der Mesh-Karte (Issue #37) | 2.1.0 | Heuristik, nicht an echter Box geprüft | Switch im Heimnetz mit Geräten dahinter · Erwartet: Eintrag „Switch“ in der Kette, nicht in den Online-Zahlen | offen |
| Wiederverwendung der Web-Sitzung (Issue #35) | 2.1.0 | Nur gegen simulierten Server geprüft; Ursache der Mails ungeklärt | Optionale Web-Funktionen einschalten, Abfrageintervall kurz · FRITZ!Box-Ereignisse zählen · Erwartet: deutlich weniger „Anmeldung an der Benutzeroberfläche“ | offen |
| Sensor „Externe IPv6“ (Issue #36) | 2.1.0 | Nicht an echter Box geprüft | Box mit IPv6 · Sensor und Attribute `prefix`, `prefix_length` ansehen | offen |
| IP ändern (Issue #38) | 2.1.0 | Nicht an echter Box geprüft | Gerät mit fester IP · „Ändern“ · neue IP wird übernommen | offen |
| „Alle ungenutzten Verbindungen entfernen“ (Dienst `remove_unused_connections`) | 2.0.2 | Weboberflächen-Schnittstelle (FRITZ!OS 8) nur im Browser beobachtet, Anfrage nie abgesendet | Testbox mit alten Einträgen · Aufräumen starten · Erwartet: nur unbenutzte Verbindungen verschwinden | offen |
| Statische IP setzen (Dienst `set_static_ip`) | 1.8.0 | Undokumentierte Weboberfläche, nach Beschreibung eines Drittprojekts, an keiner Box geprüft | Gerät ohne feste IP · IP festlegen · in der FRITZ!Box-Oberfläche prüfen | offen |
| VPN-Gegenstellen ohne MAC (Kennung `VPN:<IP>`, Issue #29) | 2.0.0 | Unbekannt, ob die Box WireGuard-Gegenstellen so meldet | Box mit WireGuard-Gegenstelle · Diagnose `box_hosts.without_mac_samples` ansehen · Eintrag erscheint in Liste und Zählern | offen |
| MAC-Filter / Pairing | 1.x | Laut README experimentell, nur mit laufendem Home Assistant abgesichert | Pairing starten und beenden · MAC-Filter schaltet wieder wie vorher | offen |


## Geprüft (Historie)

Noch keine Eintragung seit Einführung dieser Datei.
