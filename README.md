# FRITZ!Box Netzwerk

Eine Home-Assistant-Integration, die alle Geräte im FRITZ!Box-Heimnetz als sortierbare
Tabelle auf das Dashboard bringt – mit IP-Adresse, MAC-Adresse, Verbindungsart und dem
passenden Home-Assistant-Gerätenamen.

![Version](https://img.shields.io/badge/Version-1.5.2-blue)
![HACS](https://img.shields.io/badge/HACS-Custom-orange)

---

## Inhalt

- [Was die Integration kann](#was-die-integration-kann)
- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Einrichtung](#einrichtung)
- [Einstellungen](#einstellungen)
- [Sensoren](#sensoren)
- [Mesh: FRITZ!Box und Repeater als Gruppe](#mesh-fritzbox-und-repeater-als-gruppe)
- [Repeater als eigene Geräte](#repeater-als-eigene-geräte)
- [MAC-Filter und Pairing](#mac-filter-und-pairing)
- [Dashboard-Karte](#dashboard-karte)
  - [Spalten](#spalten)
  - [Sortieren, filtern, suchen](#sortieren-filtern-suchen)
  - [Steuerungsleiste und Kategorien als Tabs](#steuerungsleiste-und-kategorien-als-tabs)
  - [Wischen und Blättern auf dem Smartphone](#wischen-und-blättern-auf-dem-smartphone)
  - [IP-Adresse öffnet die Weboberfläche](#ip-adresse-öffnet-die-weboberfläche)
  - [Detail-Popup](#detail-popup)
  - [Farben](#farben)
  - [Beispiel-YAML](#beispiel-yaml)
- [Dienste](#dienste)
- [Fehlerbehebung](#fehlerbehebung)
- [Bekannte Einschränkungen](#bekannte-einschränkungen)
- [Entwicklung und Tests](#entwicklung-und-tests)
- [Versionshistorie](#versionshistorie)

---

## Was die Integration kann

- Alle bekannten Netzwerkgeräte der FRITZ!Box als **eine** Tabelle im Dashboard
- **Sortierbar** durch Klick auf jede Spaltenüberschrift, auch per Tastatur
- **Suchfeld** über Name, IP-Adresse, MAC-Adresse, Modell und Home-Assistant-Namen
- **Filterleiste**: Alle, Aktiv, Inaktiv, Gast, Gesperrt, Update – jeder Button **einzeln
  ausblendbar**
- **Home-Assistant-Gerätename** je Zeile, automatisch über die MAC-Adresse zugeordnet und
  **als Link zum HA-Gerät**
- **Detail-Popup** bei Klick auf eine Zeile: zeigt alle Felder eines Geräts – auch die
  auf schmalen Karten ausgeblendeten wie die MAC-Adresse –, mit Kopier-Knöpfen,
  Wake-on-LAN und Sprung zum Home-Assistant-Gerät
- **Wischen und Blättern** auf dem Smartphone: alle Spalten per Wischen oder Pfeilen
  erreichbar, Gerätename bleibt dabei stehen
- **Feststehender Kopf, scrollbarer Datenbereich**: eine festlegbare Zeilenzahl anzeigen,
  darüber scrollen – Titel, Auswahl und Tabellenüberschrift bleiben stehen
- **Klick auf die IP-Adresse** öffnet die Weboberfläche des Geräts im Browser
- **Zuletzt online** je Gerät – von der Integration mitgeschrieben, da die FRITZ!Box das
  nicht liefert
- **Internetzugang schalten** per Dienst oder Popup-Knopf (experimentell)
- **IP-Typ** (DHCP oder statisch) inklusive Restlaufzeit der DHCP-Zuweisung
- **Internetzugang gesperrt** (Kindersicherung) und **Firmware-Update verfügbar** auf
  einen Blick
- Vollständig über die Oberfläche konfigurierbar, inklusive **frei wählbarer Farben**
- Zwei zusätzliche Zähler-Sensoren für Automatisierungen
- **Verbindungs-Sensoren**: aktuelle Download-/Upload-Rate und die Leitungs-Sync-Raten
- **Mesh-Gruppe**: FRITZ!Box und Repeater als eine Einheit – mit Online-Zähler in Home Assistant
  und in der Karte, dazu ein Button **„Alle FRITZ!-Geräte neu starten“** (Repeater zuerst, Box zuletzt)
- **WLAN-MAC-Filter** ein-/ausschalten und **temporär freigeben („Pairing“)**: neue Geräte
  für ein paar Minuten ins WLAN lassen, danach schaltet sich der Filter selbst wieder ein

Die Karte wird von der Integration mitgeliefert und automatisch als Lovelace-Ressource
eingetragen. Es ist keine separate Installation der Karte nötig.

---

## Voraussetzungen

- Home Assistant 2024.11 oder neuer
- Eine FRITZ!Box mit aktiviertem **„Zugriff für Anwendungen zulassen"**
  (Heimnetz → Netzwerk → Netzwerkeinstellungen)
- Ein FRITZ!Box-Benutzer mit der Berechtigung **„FRITZ!Box Einstellungen"**

Getestet gegen die TR-064-Schnittstellendokumentation von AVM (Hosts-Service, Version 31
vom 11.09.2025).

---

## Installation

### Über HACS (empfohlen)

1. In HACS → Integrationen → Menü oben rechts → **Benutzerdefinierte Repositories**
2. `https://github.com/Meine-smarte-Welt/fritzbox_netzwerk` als Kategorie *Integration*
   hinzufügen
3. „FRITZ!Box Netzwerk" installieren
4. Home Assistant neu starten

### Manuell

Den Ordner `custom_components/fritzbox_netzwerk` in das `config`-Verzeichnis von Home
Assistant kopieren und neu starten.

---

## Einrichtung

Einstellungen → Geräte & Dienste → **Integration hinzufügen** → „FRITZ!Box Netzwerk".

| Feld | Bedeutung |
| --- | --- |
| Adresse | Hostname oder IP-Adresse, üblicherweise `fritz.box` |
| Benutzername | FRITZ!Box-Benutzer mit der Berechtigung „FRITZ!Box Einstellungen" |
| Kennwort | Das zugehörige Kennwort |
| Verschlüsselt verbinden | HTTPS statt HTTP zur FRITZ!Box |

Die Zugangsdaten werden beim Anlegen sofort geprüft: erreichbar, Anmeldung gültig und
Hosts-Dienst nutzbar. Schlägt eines davon fehl, nennt der Dialog die konkrete Ursache,
statt später still keine Daten zu liefern.

---

## Einstellungen

Über *Konfigurieren* an der eingerichteten Integration:

| Einstellung | Standard | Bedeutung |
| --- | --- | --- |
| Abfrageintervall | 60 s | Wie oft die Geräteliste geholt wird (15–3600 s) |
| IP-Typ erfassen | an | Ob DHCP/statisch ermittelt wird |
| Intervall der IP-Typ-Abfrage | 15 min | Takt der IP-Typ-Erfassung |
| Geräte-Tracker anlegen | aus | Ein `device_tracker` je Netzwerkgerät (zuhause/abwesend) |
| Repeater als eigene Geräte anlegen | an | Ein Home-Assistant-Gerät je AVM-Repeater sowie Mesh-Sensor und „Alle neu starten“-Button, siehe [Mesh](#mesh-fritzbox-und-repeater-als-gruppe) und [Repeater als eigene Geräte](#repeater-als-eigene-geräte) |
| FRITZ!Box-Steuerung (experimentell) | aus | WLAN-Schalter, MAC-Filter-Schalter, Pairing-Button, Buttons Neuverbinden und Neustart sowie „Alle FRITZ!-Geräte neu starten“ |
| Pairing-Dauer | 5 min | Wie lange der MAC-Filter beim Pairing ausgeschaltet bleibt (1–120 min), siehe [MAC-Filter und Pairing](#mac-filter-und-pairing) |

**Warum zwei Intervalle?** Die komplette Geräteliste kommt mit einem einzigen Aufruf von
der FRITZ!Box. Die Angabe, ob eine IP-Adresse fest zugewiesen ist, steht dort aber nicht
drin – AVM liefert sie nur einzeln je Gerät. Bei 60 Geräten wären das 60 zusätzliche
Aufrufe pro Durchlauf. Da sich dieser Wert praktisch nie ändert, läuft er in einem
eigenen, langsamen Takt. Wer die Spalte nicht braucht, schaltet die Erfassung ab und
spart die Aufrufe vollständig.

---

## Sensoren

| Sensor | Zustand | Zweck |
| --- | --- | --- |
| `sensor.<name>_gerate` | Anzahl verbundener Geräte | Trägt die komplette Geräteliste im Attribut `hosts`; Datenquelle der Karte |
| `sensor.<name>_gerate_mit_update` | Anzahl | Automatisierung „neue Firmware verfügbar" |
| `sensor.<name>_gesperrte_gerate` | Anzahl | Überwachung der Kindersicherung |
| `sensor.<name>_download` | kB/s | Aktuelle Download-Rate der Internetverbindung |
| `sensor.<name>_upload` | kB/s | Aktuelle Upload-Rate der Internetverbindung |
| `sensor.<name>_mesh` | Anzahl online | Erreichbare FRITZ!-Geräte (Box + Repeater), Attribute `gesamt`, `vollstaendig`, `members`; nur mit Repeatern, siehe [Mesh](#mesh-fritzbox-und-repeater-als-gruppe) |
| `sensor.<name>_download_leitungsrate` | Mbit/s | Maximale Downstream-Rate der Leitung (Sync) |
| `sensor.<name>_upload_leitungsrate` | Mbit/s | Maximale Upstream-Rate der Leitung (Sync) |

Die vier Down/Up-Sensoren nutzen die WAN-Dienste der FRITZ!Box (TR-064). Fehlt der
WAN-Dienst – etwa wenn die FRITZ!Box als reiner Access Point läuft –, bleiben diese Sensoren
„unbekannt", ohne die Geräteliste zu beeinträchtigen.

Die Einheit der drei Zähler-Sensoren (*Geräte* / *devices* / *apparaten*) folgt der in Home
Assistant eingestellten Sprache.

Das Attribut `hosts` ist per `_unrecorded_attributes` vom Recorder ausgenommen. Ohne das
schriebe Home Assistant die vollständige Geräteliste bei jeder Änderung in die Datenbank –
bei 60 Geräten rund 15–20 kB pro Eintrag.

Weitere Attribute am Hauptsensor: `gesamt`, `aktiv`, `inaktiv`, `gastnetz`, `gesperrt`,
`updates_verfuegbar`, `statische_ip`, `letzte_abfrage`, `letzte_ip_typ_abfrage`.

---

## Mesh: FRITZ!Box und Repeater als Gruppe

Die FRITZ!Box und ihre AVM-Repeater bilden zusammen das Mesh. Die Integration behandelt sie
als **eine Gruppe**: in Home Assistant, in der Karte und beim Neustart.

**In Home Assistant.** Die Repeater hängen als eigene Geräte unter der FRITZ!Box („Verbunden
über“), die Geräteseite der Box zeigt sie als angeschlossene Geräte. Dazu gibt es am
FRITZ!Box-Gerät:

| Entität | Zweck |
| --- | --- |
| `sensor.<name>_mesh` | Zahl der erreichbaren FRITZ!-Geräte (Box + Repeater). Attribute: `gesamt`, `vollstaendig` (`true`, wenn alle erreichbar sind) und `members` mit Rolle, Name, Modell, IP-Adresse und Online-Status je Gerät – etwa für die Automation „ein Repeater ist ausgefallen“ |
| `button.<name>_alle_fritz_gerate_neu_starten` | Startet **alle** FRITZ!-Geräte neu, siehe unten. Nur mit *FRITZ!Box-Steuerung* |

Beide Entitäten entstehen erst, wenn es neben der Box mindestens einen Repeater gibt, und sind
mit der Option *Repeater als eigene Geräte anlegen* abschaltbar. Die Box selbst zählt als
erreichbar, sobald sie antwortet.

**Alle neu starten – so läuft es ab.**

1. Zuerst werden **die Repeater** neu gestartet, einer nach dem anderen, jeweils direkt über
   ihr eigenes TR-064 (siehe [Repeater als eigene Geräte](#repeater-als-eigene-geräte)).
   Repeater, die gerade offline sind oder keine IP-Adresse haben, werden übersprungen und im
   Protokoll vermerkt.
2. Nach einer kurzen Pause von drei Sekunden folgt **die FRITZ!Box**. Die Reihenfolge ist
   Absicht: Die Repeater werden über das Netz der Box angesprochen – wäre die Box zuerst weg,
   käme der Befehl bei ihnen nicht mehr an.
3. Schlägt ein Repeater fehl, laufen die übrigen und die Box trotzdem durch. Zum Schluss meldet
   Home Assistant, welche Repeater sich nicht neu starten ließen. Scheitert die Box selbst,
   steht in der Meldung, wie viele Repeater bereits neu gestartet wurden.

Das Heimnetz ist danach für einige Minuten offline, auch Home Assistant verliert währenddessen
die Verbindung zur FRITZ!Box. Der Dienst dafür:

```yaml
action: fritzbox_netzwerk.reboot_mesh
```

**In der Karte** erscheint in der Steuerungsleiste (Editor: *Steuerungsleiste anzeigen*) ein
Rahmen „Mesh“ mit dem Online-Zähler („3 von 3 online“), der FRITZ!Box und jedem Repeater samt
Status – ein ausgefallener Repeater färbt den Rahmen rot und erscheint abgeblendet. Ist die
FRITZ!Box-Steuerung aktiv, sitzt im Rahmen der Button **Alle neu starten**; er verlangt wie
*Neustart* zwei Klicks (der erste färbt ihn, erst der zweite löst aus). Ohne Repeater
erscheint der Rahmen nicht.

**Hinweise.**

- Der Sammel-Neustart setzt voraus, dass die Repeater die Anmeldung mit den Zugangsdaten der
  FRITZ!Box akzeptieren – dieselbe Bedingung wie beim Neustart eines einzelnen Repeaters.
- Erkannt werden Repeater am Modell („…Repeater…“); andere Mesh-Geräte, etwa Powerline-Adapter
  mit Mesh-Funktion, gehören derzeit nicht zur Gruppe.
- Die Funktion ist neu und konnte ohne Repeater-Hardware nicht getestet werden –
  Rückmeldungen als GitHub-Issue willkommen.

---

## Repeater als eigene Geräte

AVM-Repeater im Mesh erscheinen in der Geräteliste der FRITZ!Box wie jedes andere
Netzwerkgerät. Die Integration legt für jeden von ihnen zusätzlich ein
**eigenes Home-Assistant-Gerät** an, das an der FRITZ!Box hängt. Erkannt wird ein Repeater
daran, dass sein von der FRITZ!Box gemeldetes Modell „Repeater“ enthält (etwa
*FRITZ!Repeater 1200 AX*) – der Name wird nicht geraten.

| Entität | Wann | Zweck |
| --- | --- | --- |
| `binary_sensor.<repeater>_verbunden` | immer | Ist der Repeater gerade mit der FRITZ!Box verbunden? Für Ausfall-Automationen |
| `button.<repeater>_neustart` | nur mit *FRITZ!Box-Steuerung* | Startet den Repeater neu |

Neu auftauchende Repeater werden automatisch ergänzt. Wer das nicht möchte, schaltet
*Repeater als eigene Geräte anlegen* in den Einstellungen der Integration aus.

**So funktioniert der Neustart.** Die Hauptbox kann fremde Geräte nicht neu starten. Die
Integration verbindet sich deshalb mit denselben Zugangsdaten direkt mit dem Repeater
(TR-064 an dessen IP-Adresse) und löst dort den Neustart aus. Das setzt voraus, dass der
Repeater diese Anmeldung akzeptiert. Im Mesh übernehmen Repeater in der Regel die Zugangsdaten
der FRITZ!Box; ist das bei dir nicht so oder ist der Zugriff für Anwendungen am Repeater
abgeschaltet, meldet der Button, dass der Repeater die Anmeldung abgelehnt hat.

**Die Zeile des Repeaters in der Karte** verweist – über die MAC-Adresse – auf dieses Gerät.

Alle Repeater zusammen mit der FRITZ!Box als Gruppe – samt Sammel-Neustart – beschreibt der
nächste Abschnitt.

---

## MAC-Filter und Pairing

Die FRITZ!Box kann das WLAN auf **bekannte Geräte beschränken** (WLAN → Sicherheit →
*Zugang auf bekannte WLAN-Geräte beschränken*, im Folgenden „MAC-Filter“). Ist der Filter an,
kommt ein neues Gerät auch mit dem richtigen WLAN-Kennwort nicht hinein. Das lässt
sich aus Home Assistant steuern – mit *FRITZ!Box-Steuerung* aktiviert:

| Entität | Zweck |
| --- | --- |
| `switch.<name>_mac_filter` | Filter dauerhaft **ein** oder **aus** |
| `button.<name>_pairing_starten` | Filter für die eingestellte Zeit ausschalten, danach **automatisch wieder ein** |

Die Entitäten erscheinen nur, wenn die FRITZ!Box den Filter über TR-064 meldet.

**Pairing – so läuft es ab.**

1. Filter ist an. Du drückst *Pairing starten* (Button, Karte oder Dienst).
2. Die Integration merkt sich den Endzeitpunkt, plant das Wiedereinschalten und schaltet
   *danach* den Filter aus. Der Schalter zeigt jetzt *aus* und hat die Attribute
   `pairing_active: true` und `pairing_ends`.
3. Du verbindest das neue Gerät mit dem WLAN.
4. Nach Ablauf der Pairing-Dauer schaltet die Integration den Filter wieder ein. Ist das
   Gerät früher verbunden, genügt ein Klick auf den Schalter (*ein*), dann ist das Fenster
   sofort zu.

Ein Klick auf den Schalter beendet immer ein laufendes Pairing: *Einschalten* schließt das
Fenster sofort, *Ausschalten* macht die Freigabe dauerhaft. Ein erneuter Klick auf
*Pairing starten* während eines laufenden Pairings verlängert das Fenster um die volle
Dauer ab jetzt.

**Sicherheit vor Vergessen.** Der Endzeitpunkt wird gespeichert. Wird Home Assistant
während des Pairings neu gestartet, plant die Integration beim Start den Termin neu – oder
schaltet den Filter sofort ein, falls die Frist inzwischen verstrichen ist. Erreicht die
Integration die FRITZ!Box zum Ablauf nicht, versucht sie es jede Minute erneut. Schlägt das
Ausschalten beim Start des Pairings selbst fehl, wird der Filter, soweit nötig, wieder
eingeschaltet, statt halb offen zu bleiben. **Wichtig:** Solange Home Assistant nicht läuft,
kann auch nichts wieder eingeschaltet werden – das passiert dann erst beim nächsten Start.

**Pairing startet nur bei eingeschaltetem Filter.** Ist der Filter aus, gäbe es nichts
„temporär“ auszuschalten; der Button meldet das, statt später einen Filter einzuschalten,
den du nie hattest.

**Die Karte** zeigt in der Steuerungsleiste einen *MAC-Filter*-Chip (gedrückt = Filter an)
und daneben, solange der Filter an ist, den Button *Pairing*. Läuft ein Pairing, steht im
Chip „Pairing bis HH:MM“; ein Klick beendet es sofort.

**Dienste.**

```yaml
# Filter dauerhaft schalten
action: fritzbox_netzwerk.set_mac_filter
data:
  enabled: false
```

```yaml
# Pairing mit der in den Einstellungen gewählten Dauer
action: fritzbox_netzwerk.start_pairing

# ... oder mit eigener Dauer (1-120 Minuten)
action: fritzbox_netzwerk.start_pairing
data:
  minutes: 10
```

**Technik.** Der Filter steckt in `WLANConfiguration<n>` (TR-064). Die Aktion `SetConfig`
verlangt dort alle Werte auf einmal; die Integration liest deshalb zuerst `GetInfo` und
schreibt die aktuellen Werte unverändert mit zurück – nur der Filter-Wert ändert sich. Danach
wird nachgelesen, ob die Box die Änderung übernommen hat. Der Filter gilt für die
Hauptbänder (2,4 und 5 GHz); das Gast-WLAN wird nicht angefasst. Auf Boxen mit nur einem Band
ist der zweite WLAN-Dienst das Gastnetz und bleibt deshalb außen vor.

**Bitte beachten.**

- Je nach Modell und FRITZ!OS kann die Box das WLAN beim Schreiben von `SetConfig` kurz neu
  initialisieren; bereits verbundene Geräte verbinden sich dann selbst neu.
- Ob die FRITZ!Box ein Gerät, das sich während des Pairings anmeldet, danach als „bekannt“
  führt und beim Wiedereinschalten weiter zulässt, ist AVMs Verhalten und hängt vom
  FRITZ!OS ab. Prüfe es beim ersten Einsatz mit einem Testgerät.
- Die Funktion ist neu und konnte ohne FRITZ!Box nicht getestet werden – Rückmeldungen als
  GitHub-Issue willkommen.

---

## Dashboard-Karte

Karte hinzufügen → **FRITZ!Box Netzwerk** → Sensor auswählen. Alles Weitere lässt sich im
grafischen Editor einstellen.

### Spalten

| Spalte | Standard | Quelle |
| --- | --- | --- |
| Status | an | `Active` – farbiger Punkt |
| Gerät | an | Name aus der FRITZ!Box, samt Abzeichen für Gast, VPN und Priorität |
| IP-Adresse | an | `IPAddress` |
| MAC-Adresse | an | `MACAddress` |
| Verbindung | an | `InterfaceType` + Portnummer, z. B. „LAN 2" oder „WLAN (Gast)" |
| Home Assistant | an | Gerätename aus der Geräteregistrierung |
| IP-Typ | an | DHCP oder statisch, mit Lease-Restzeit |
| Internet | an | Internetzugang gesperrt (Kindersicherung) |
| Update | an | Firmware-Update für das Gerät verfügbar |
| Tempo | an | `X_AVM-DE_Speed` in Mbit/s bzw. Gbit/s |
| Modell | aus | Nur AVM-Geräte melden hier etwas |
| Gerätetyp | aus | Automatisch erkannte bzw. vom Nutzer gesetzte Geräteklasse |
| Zuletzt online | aus | Wann das Gerät zuletzt aktiv war (von der Integration mitgeschrieben) |

Passen auf einer schmalen Karte – etwa in einer schmalen Dashboard-Spalte oder auf dem
Telefon – nicht alle Spalten nebeneinander, wird die Tabelle waagerecht scrollbar. So
bleiben auch die hinteren Spalten wie *Home Assistant* erreichbar. Näheres unter
[Wischen und Blättern auf dem Smartphone](#wischen-und-blättern-auf-dem-smartphone).

### Sortieren, filtern, suchen

Klick oder Enter auf eine Spaltenüberschrift sortiert nach dieser Spalte, ein zweiter Klick
dreht die Richtung. IP-Adressen werden dabei numerisch sortiert, `192.168.178.9` steht also
korrekt vor `192.168.178.10`. Startsortierung und -richtung lassen sich im Editor
festlegen.

Die Karte startet standardmäßig mit dem Filter **Aktiv**, zeigt also zuerst nur verbundene
Geräte. Wer lieber mit **Alle** (oder einem anderen Filter) beginnen möchte, stellt im Editor
unter *Filter-Buttons* den *Standardfilter beim Laden* um bzw. setzt im YAML
`default_filter: alle`. Ist der Button des Standardfilters ausgeblendet, fällt die Karte auf
*Alle* zurück.

Suchfeld und Filterleiste arbeiten zusammen: „Aktiv" plus Suchbegriff zeigt nur verbundene
Geräte, auf die der Begriff passt. Beide Bedienelemente behalten ihren Inhalt, wenn der
Sensor im Hintergrund neue Daten liefert.

### Steuerungsleiste und Kategorien als Tabs

Der Editor-Schalter *Steuerungsleiste anzeigen* blendet in der Karte eine zusätzliche Leiste
ein: die **Live-Werte für Download und Upload** und – sofern die FRITZ!Box-Steuerung in den
Integrationseinstellungen aktiviert ist – die **Schalter für die WLAN-Bänder** (2,4 GHz,
5 GHz, Gast), der **MAC-Filter** mit dem Button **Pairing** (siehe
[MAC-Filter und Pairing](#mac-filter-und-pairing)) sowie die Buttons **Neuverbinden** (neue
öffentliche IP) und **Neustart**. Gibt es Repeater, kommt die **Mesh-Gruppe** mit dem Button
**Alle neu starten** hinzu (siehe [Mesh](#mesh-fritzbox-und-repeater-als-gruppe)). Der
Neustart verlangt zwei Klicks: der erste Klick färbt den Button, erst der zweite löst
tatsächlich aus.

Der Schalter *Kategorien als Tabs anzeigen* (standardmäßig aus) setzt darüber eine
Reiterleiste im Stil von *FRITZ!Box Anrufe*:

| Reiter | Was darin erscheint |
| --- | --- |
| **Netzwerk** (`mdi:lan`) | Filterleiste, Suchfeld, Zusammenfassung, Geräteliste |
| **Steuerung** (`mdi:router-wireless-settings`) | Download/Upload, WLAN-Schalter, MAC-Filter, Pairing, Neuverbinden, Neustart, Mesh-Gruppe |

Die Trennung ist strikt: Im Reiter *Netzwerk* erscheinen keine Steuerungselemente, im Reiter
*Steuerung* keine Filter, kein Suchfeld und keine Geräteliste. Es wird nichts doppelt
angezeigt.

Der Reiter *Steuerung* wird nur angelegt, wenn es tatsächlich etwas zu steuern gibt – also
wenn die Steuerungsleiste eingeschaltet ist und die FRITZ!Box entsprechende Werte liefert.
Gibt es nur eine Kategorie, verschwindet die Reiterleiste ganz, statt einen toten Reiter zu
zeigen.

Sind die Tabs ausgeschaltet (Standard), verhält sich die Karte wie bisher: Filter, Suche,
Liste und – falls aktiviert – die Steuerungsleiste erscheinen gemeinsam untereinander in
einer einzigen Ansicht.

### Wischen und Blättern auf dem Smartphone

Passen nicht alle Spalten nebeneinander, wird die Tabelle waagerecht scrollbar. Auf dem
Telefon lässt sich einfach mit dem Finger nach links und rechts wischen, um die hinteren
Spalten (MAC-Adresse, Home Assistant, IP-Typ, Tempo …) einzusehen. Zusätzlich erscheinen
am linken und rechten Rand **Pfeile**, die sich auch anklicken lassen – jeder Klick blättert
etwa eine halbe Kartenbreite weiter. Die Pfeile erscheinen nur, wenn in ihre Richtung noch
etwas verborgen ist.

Statuspunkt und Gerätename bleiben beim Blättern links stehen, damit immer klar ist, zu
welchem Gerät die Werte gehören. Beides ist im Editor abschaltbar: *Blätter-Pfeile bei
breiter Tabelle* und *Gerätename beim Blättern festhalten*.

### IP-Adresse öffnet die Weboberfläche

Ein Klick auf die IP-Adresse öffnet die Weboberfläche des Geräts in einem neuen
Browser-Tab. Bevorzugt wird die Adresse, die die FRITZ!Box selbst zum Gerät meldet;
ist keine hinterlegt, wird `http://<IP>` versucht (abschaltbar über *Notfalls http://IP
verwenden*). Aus Sicherheitsgründen werden ausschließlich `http`- und `https`-Adressen
geöffnet. Der Klick auf die IP öffnet nicht zusätzlich das Detail-Popup; das steht über den
Rest der Zeile weiter zur Verfügung. Im Popup selbst gibt es dafür den Knopf *Weboberfläche
öffnen*.

Geräte ohne eigene Weboberfläche (viele IoT-Geräte, Sensoren) beantworten `http://<IP>`
nicht – dann zeigt der Browser einen Fehler. Wer das vermeiden möchte, schaltet den
Fallback ab; dann sind nur Geräte verlinkt, für die die FRITZ!Box tatsächlich eine Adresse
meldet.

### Detail-Popup

Ein Klick oder Enter auf eine Zeile öffnet ein Popup mit **allen** Angaben zum Gerät – auch
den Feldern, die auf einer schmalen Karte gerade aus dem sichtbaren Bereich gescrollt sind.
IP- und MAC-Adresse lassen sich dort mit einem Knopf in die Zwischenablage kopieren.

Je nach Gerät bietet das Popup zusätzlich:

- **In Home Assistant öffnen** – springt zur Geräteseite, sofern das Gerät in Home
  Assistant über seine MAC-Adresse bekannt ist
- **Aufwecken (WoL)** – sendet ein Wake-on-LAN-Signal, wird nur bei nicht verbundenen
  Geräten angezeigt
- **Anwesenheit** – diese Zeile steht immer im Popup und zeigt den
  Zustand der zugehörigen `device_tracker`-Entität: *zuhause* bzw. *abwesend*, verlinkt auf
  die Entität (ein Klick öffnet deren Info-Dialog). Gibt es keinen nutzbaren Tracker, sagt
  die Zeile, warum: *nicht aktiviert* (Device Tracker ist in den Integrationseinstellungen
  ausgeschaltet – der Tooltip nennt den Weg dorthin), *Entität deaktiviert* (die Entität ist
  in Home Assistant ausgeschaltet) oder „—" (für dieses Gerät gibt es keinen Tracker)

Das Popup ist der Standard. Wer stattdessen wie bisher direkt zur Home-Assistant-Geräteseite
springen möchte, schaltet im Editor *Klick öffnet ein Detail-Popup* ab; dann greift wieder
*Klick öffnet das Home-Assistant-Gerät*.

### Farben

Alle zwölf Farben lassen sich im Abschnitt *Farben* des Editors setzen – wahlweise per
Texteingabe (Hex, `rgb()`, `hsl()`, CSS-Farbname oder `var(--…)`) oder über die grafische
Farbauswahl. Zu jeder Farbe zeigt der Editor, welcher Wert aktuell greift. Ein Klick auf
*Alle Farben zurücksetzen* leert alle zwölf Werte in einem Zug.

Leer bedeutet: die Karte folgt dem aktiven Theme. Gesetzte Farben sind normale
Lovelace-Kartenkonfiguration und werden von Home Assistants eigener Dashboard-Speicherung
verwaltet – diese Integration hat dafür keinen eigenen Speicher.

### Beispiel-YAML

```yaml
type: custom:fritzbox-netzwerk-card
entity: sensor.fritz_box_5690_pro_netzwerk_gerate
title: Heimnetz
show_title: true

# Spalten
show_status: true
show_name: true
show_ip: true
show_mac: true
show_connection: true
show_ha_name: true
show_ip_type: true
show_wan: true
show_update: true
show_speed: true
show_model: false
show_type: false
show_last_seen: false

# Darstellung
show_summary: true
show_search: true
show_filter: true
# einzelne Filter-Buttons
filter_alle: true
filter_aktiv: true
filter_inaktiv: true
filter_gast: true
filter_gesperrt: true
filter_update: true
default_filter: aktiv   # alle | aktiv | inaktiv | gast | gesperrt | update
hide_inactive: false
compact: false
show_details_popup: true
open_device_on_click: true
show_scroll_arrows: true
sticky_name: true
ip_opens_web: true
ip_web_fallback: true
max_rows: 0
max_visible_rows: 0   # 0 = alle; z. B. 15 = danach scrollen

# Sortierung
sort_by: ip
sort_dir: asc

# Farben (leer = Theme)
color_active: "#43a047"
color_blocked: "#db4437"
```

---

## Dienste

### `fritzbox_netzwerk.set_device_name`

Benennt ein Netzwerkgerät in der FRITZ!Box um.

```yaml
action: fritzbox_netzwerk.set_device_name
data:
  mac: "3C:A6:F6:00:11:22"
  name: "Drucker Arbeitszimmer"
```

### `fritzbox_netzwerk.wake_on_lan`

Sendet ein Wake-on-LAN-Signal.

```yaml
action: fritzbox_netzwerk.wake_on_lan
data:
  mac: "3C:A6:F6:00:11:22"
```

### `fritzbox_netzwerk.set_internet_access` (experimentell)

Sperrt oder erlaubt den Internetzugang eines Geräts. Nützlich zum Beispiel, um ein Gerät
kurz online gehen zu lassen (Update-Prüfung) und danach wieder zu sperren. Übergeben wird
die MAC-Adresse (stabiler als die IP); die aktuelle IP wird intern aufgelöst.

```yaml
# kurz freigeben, prüfen lassen, dann wieder sperren
- action: fritzbox_netzwerk.set_internet_access
  data:
    mac: "3C:A6:F6:00:11:22"
    blocked: false
- delay: "00:05:00"
- action: fritzbox_netzwerk.set_internet_access
  data:
    mac: "3C:A6:F6:00:11:22"
    blocked: true
```

Der Dienst nutzt TR-064 (`X_AVM-DE_HostFilter`). Ob er verfügbar ist, hängt von FRITZ!OS
und Modell ab – deshalb ist er als experimentell gekennzeichnet. Im Detail-Popup gibt es
denselben Schalter auch per Klick.

### `fritzbox_netzwerk.set_mac_filter` (experimentell)

Schaltet den WLAN-MAC-Filter („Zugang auf bekannte WLAN-Geräte beschränken“) ein oder aus.
Beendet ein laufendes Pairing. Voraussetzung: *FRITZ!Box-Steuerung* ist aktiviert.

```yaml
action: fritzbox_netzwerk.set_mac_filter
data:
  enabled: true
```

### `fritzbox_netzwerk.start_pairing` (experimentell)

Schaltet den MAC-Filter für `minutes` Minuten (1–120, ohne Angabe: Einstellung *Pairing-Dauer*)
aus und danach automatisch wieder ein. Nur bei eingeschaltetem Filter oder laufendem Pairing
möglich. Details unter [MAC-Filter und Pairing](#mac-filter-und-pairing).

```yaml
action: fritzbox_netzwerk.start_pairing
data:
  minutes: 5
```

### `fritzbox_netzwerk.reboot_mesh` (experimentell)

Startet alle FRITZ!-Geräte neu: zuerst die erreichbaren Repeater, nach einer kurzen Pause die
FRITZ!Box. Gleichwertig zum Button *Alle FRITZ!-Geräte neu starten*; ohne Repeater wird nur die
Box neu gestartet. Das Heimnetz ist danach einige Minuten offline. Details unter
[Mesh](#mesh-fritzbox-und-repeater-als-gruppe).

```yaml
action: fritzbox_netzwerk.reboot_mesh
```

---

## Fehlerbehebung

**Die Einrichtung meldet „Das Konto hat keinen Zugriff auf die FRITZ!Box-Einstellungen".**
In der FRITZ!Box unter System → FRITZ!Box-Benutzer beim verwendeten Konto die Berechtigung
*FRITZ!Box Einstellungen* setzen. Ein reiner Benutzer ohne diese Berechtigung kann die
Geräteliste nicht abrufen.

**Die Einrichtung meldet, der Dienst „Hosts" fehle.**
Unter Heimnetz → Netzwerk → Netzwerkeinstellungen die Option *Zugriff für Anwendungen
zulassen* aktivieren. Ohne sie ist die TR-064-Schnittstelle komplett abgeschaltet.

**Der Button *Neu verbinden* meldet einen Fehler (z. B. `errorCode: 606`).**
Bis 1.5.1 nutzte der Button den UPnP-Dienst der FRITZ!Box, den manche Boxen mit Fehler 606
(„nicht autorisiert“) ablehnen – vermutlich, weil dieser Weg an den UPnP-Einstellungen der Box
hängt und nicht an den Rechten des Kontos. Der *Neustart* ging trotzdem, weil er über TR-064
läuft. Seit 1.5.2 wird zuerst der TR-064-Weg mit der Anmeldung
der Integration versucht, der UPnP-Weg nur noch als Rückfall. Meldet der Button weiterhin
einen Fehler, prüfe, ob das Konto die Berechtigung *FRITZ!Box Einstellungen* hat und ob die
FRITZ!Box die Internetverbindung selbst aufbaut. Hängt sie hinter einem vorgeschalteten Router
oder Modem (oder ist sie ein Kabel-Modell), gibt es dort keine Einwahl, die neu aufgebaut
werden könnte.

**„Alle neu starten“ meldet, dass Repeater nicht neu gestartet werden konnten.**
Die FRITZ!Box wurde trotzdem neu gestartet, die Meldung nennt die betroffenen Repeater.
Meist lehnt der Repeater die Anmeldung ab: Am Repeater muss der Zugriff für Anwendungen
(TR-064) erlaubt sein, und er muss die Zugangsdaten der FRITZ!Box übernommen haben (im Mesh
üblich). Ein einzelner Repeater lässt sich über seinen eigenen *Neustart*-Button testen.

**Der Mesh-Sensor und der Button „Alle neu starten“ fehlen.**
Beide entstehen erst, sobald die FRITZ!Box mindestens einen Repeater in der Geräteliste führt
(Modell enthält „Repeater“), und nur bei eingeschalteter Option *Repeater als eigene Geräte
anlegen*. Der Button braucht außerdem die *FRITZ!Box-Steuerung*.

**Der MAC-Filter-Schalter und der Pairing-Button fehlen.**
Beide gibt es nur mit aktivierter *FRITZ!Box-Steuerung* und nur, wenn die Box den Filter
(`NewMACAddressControlEnabled` in `WLANConfiguration1`) über TR-064 meldet. Fehlt er, ist der
Filter auf dieser Box/FRITZ!OS-Version nicht per TR-064 erreichbar.

**Das Pairing meldet „Der MAC-Filter ist ausgeschaltet“.**
Pairing schaltet den Filter *temporär aus* und danach wieder ein. Ist er bereits aus, gibt es
nichts zu tun – schalte ihn zuerst mit dem Schalter ein.

**Die Box lehnt das Schalten des MAC-Filters ab.**
Das Konto braucht die Berechtigung *FRITZ!Box Einstellungen*. Meldet die Integration, die Box
habe die Änderung nicht übernommen, hat `SetConfig` zwar geantwortet, der Filter steht aber
weiter auf dem alten Wert; die Protokolldetails nennen dann das betroffene Band.

**Nach einem Update steht bei den Zählern eine andere Einheit / Home Assistant meldet
geänderte Einheiten.**
Die Einheit der Zähler-Sensoren (bis 1.5.1 fest „Geräte“) folgt jetzt der Sprache von Home
Assistant. Wer Home Assistant nicht auf Deutsch betreibt, kann dadurch einmalig den Hinweis sehen,
dass sich die Einheit einer Statistik geändert hat. Unter Entwicklerwerkzeuge → Statistiken
lässt sich das mit *Problem beheben* bereinigen; die Werte selbst bleiben unberührt.

**Die Spalte „IP-Typ" zeigt überall nur „—".**
Entweder ist die IP-Typ-Erfassung in den Einstellungen der Integration ausgeschaltet, oder
sie ist seit dem Start noch nicht gelaufen. Die Karte zeigt bewusst „—" statt „DHCP"
anzunehmen – die Geräteliste selbst enthält diese Angabe nicht.

**Die Spalte „Home Assistant" bleibt leer.**
Zugeordnet wird ausschließlich über die MAC-Adresse in der Geräteregistrierung. Viele
Integrationen hinterlegen dort keine MAC. Prüfbar unter Einstellungen → Geräte & Dienste →
Gerät: steht dort keine MAC-Adresse, kann keine Zuordnung stattfinden.

**Die Karte wird nach der HACS-Installation nicht gefunden / „Custom element doesn't
exist: fritzbox-netzwerk-card".**
Die Integration liefert ihre Karte selbst mit und trägt sie automatisch als
Lovelace-Ressource ein. Wird sie trotzdem nicht gefunden, hilft in dieser Reihenfolge:

1. **Browser hart neu laden** (Strg/Cmd+Shift+R). In der Companion-App zusätzlich den
   App-Zwischenspeicher leeren. Die Karte wird oft nur wegen einer alten zwischengespeicherten
   Datei nicht gefunden.
2. Prüfen, ob die Ressource eingetragen ist: Einstellungen → Dashboards → Menü oben rechts →
   *Ressourcen*. Es sollte ein Eintrag `/fritzbox_netzwerk/fritzbox-netzwerk-card.js`
   (Typ *JavaScript-Modul*) vorhanden sein.
3. Fehlt er, manuell hinzufügen: *Ressource hinzufügen* → URL
   `/fritzbox_netzwerk/fritzbox-netzwerk-card.js`, Typ *JavaScript-Modul* → speichern und den
   Browser neu laden. (Im YAML-Dashboard-Modus verwaltet Home Assistant Ressourcen nicht über
   die Oberfläche – dort den Eintrag in der `lovelace:`-Konfiguration ergänzen.)

**Die Karte ist da, zeigt aber keine Geräte („Keine Geräte gefunden").**
- Ist beim Anlegen der Karte der richtige Sensor gewählt? Es muss der Sensor mit der
  Geräteliste sein, üblicherweise `sensor.<name>_gerate` (der Zustand ist die Anzahl aktiver
  Geräte). Unter Entwicklerwerkzeuge → Zustände lässt sich prüfen, ob dieser Sensor das
  Attribut `hosts` mit Einträgen enthält.
- Ist ein Filter aktiv (z. B. „Gesperrt") oder ein Suchbegriff gesetzt, der nichts trifft?
  Auf „Alle" stellen und das Suchfeld leeren.
- Ist der Sensor „nicht verfügbar", liegt es an der Integration selbst – dann Protokoll
  prüfen (Berechtigungen, Erreichbarkeit) wie oben beschrieben.

---

## Sprachen

Sowohl die **Integration** (Einrichtung, Dienste) als auch die **Dashboard-Karte** – inklusive
ihres **Konfigurations-Editors** – sind auf
**Deutsch**, **Englisch** und **Niederländisch** übersetzt (`de`, `en`, `nl`). Die Karte
folgt automatisch der in Home Assistant eingestellten Sprache; fehlt eine Übersetzung, wird
auf Deutsch zurückgefallen.

Wer die Kartensprache unabhängig von Home Assistant festlegen möchte, wählt sie im
Karten-Editor unter *Sprache der Karte* (Automatisch / Deutsch / English / Nederlands) oder
setzt sie im YAML:

```yaml
type: custom:fritzbox-netzwerk-card
entity: sensor.fritz_box_netzwerk_gerate
language: nl   # "" = automatisch, sonst de | en | nl
```

---

## Bekannte Einschränkungen

- **Statische IP-Adressen lassen sich nicht ändern.** Die TR-064-Schnittstelle von AVM
  kennt dafür keine Aktion. Schreibbar sind dort nur Gerätename, Anzeigename,
  Wake-on-LAN, Echtzeitpriorität und Geräteklasse. Ein Setzen der IP-Adresse wäre nur über
  die Weboberfläche der FRITZ!Box möglich – undokumentiert und bei jedem FRITZ!OS-Update
  potenziell defekt. Das ist bewusst nicht Teil dieser Version.
- **Mesh nur in Teilen.** FRITZ!Box und Repeater bilden eine Gruppe (siehe oben). WLAN-Band,
  Signalstärke und der Repeater, an dem ein Gerät hängt, stehen dagegen in einer eigenen
  Schnittstelle (`X_AVM-DE_GetMeshListPath`) und sind noch nicht ausgewertet.
- **MAC-Filter/Pairing ist experimentell** und nur mit laufendem Home Assistant abgesichert:
  Das automatische Wiedereinschalten übernimmt die Integration, nicht die FRITZ!Box.
- **Repeater-Neustart und „Alle neu starten“ sind experimentell.** Sie hängen davon ab, dass
  der Repeater die Anmeldung mit den Zugangsdaten der FRITZ!Box akzeptiert.
- **Nur eine FRITZ!Box je Dienstaufruf.** Sind mehrere Boxen eingerichtet, wirken
  `set_device_name` und `wake_on_lan` auf die zuerst geladene.
- Die Zuordnung zu Home-Assistant-Geräten erfolgt ausschließlich über die MAC-Adresse.
  Es wird bewusst nicht über Namensähnlichkeit geraten.

---

## Entwicklung und Tests

Die eigentliche Aufbereitungslogik liegt in `hosts.py` und enthält weder
Home-Assistant- noch fritzconnection-Importe. Sie ist damit ohne laufende
Home-Assistant-Instanz prüfbar:

```bash
python3 tests/test_hosts.py     # 41 Fälle
node tests/test_card.js         # 134 Fälle, jsdom gegen die echte Kartendatei
node tests/test_card_tabs.js    # 39 Fälle, Kategorien/Tabs und Steuerungsleiste
node tests/test_tracker_popup.js # 23 Fälle, Anwesenheits-Zeile im Detail-Popup
```

Die JS-Tests laden die ausgelieferte `fritzbox-netzwerk-card.js` unverändert in ein echtes
DOM und steuern die Karte genau so an, wie Lovelace es tut – über `setConfig()`, den
`hass`-Setter und echte Klick- und Tastaturereignisse. Es gibt keine zweite Kopie des
Kartencodes im Testaufbau.

---

## Versionshistorie

### 1.5.2 – Mesh-Gruppe, MAC-Filter/Pairing, Repeater als Geräte, Reconnect-Fix

**Neu**

- **Mesh-Gruppe: FRITZ!Box und Repeater als eine Einheit.** Neuer Sensor `sensor.<name>_mesh`
  (Zahl der erreichbaren FRITZ!-Geräte, Attribute `gesamt`, `vollstaendig`, `members`) und in der
  Karte ein Rahmen „Mesh“ mit Online-Zähler und Status jedes Geräts. Details unter
  [Mesh](#mesh-fritzbox-und-repeater-als-gruppe).
- **Neu: „Alle FRITZ!-Geräte neu starten“.** Button `button.<name>_alle_fritz_gerate_neu_starten`,
  Dienst `fritzbox_netzwerk.reboot_mesh` und Button in der Karte (mit Zwei-Klick-Bestätigung).
  Erst die Repeater, dann die FRITZ!Box; ein fehlgeschlagener Repeater hält die übrigen nicht auf,
  offline Repeater werden übersprungen.
- **Neu: WLAN-MAC-Filter ein-/ausschalten.** Schalter `switch.<name>_mac_filter` (mit aktivierter
  *FRITZ!Box-Steuerung*) und Dienst `fritzbox_netzwerk.set_mac_filter`.
- **Neu: MAC-Filter temporär ausschalten – „Pairing“.** Button `button.<name>_pairing_starten` und
  Dienst `fritzbox_netzwerk.start_pairing` schalten den Filter für eine einstellbare Zeit aus und
  danach von selbst wieder ein. Neue Option *Pairing-Dauer* (Standard 5 min, 1–120).
  Ausfallsicher gebaut: Der Endzeitpunkt wird vor dem Ausschalten gespeichert, überlebt einen
  Neustart von Home Assistant, das Wiedereinschalten wird bei Fehlern jede Minute wiederholt,
  ein fehlgeschlagener Start wird zurückgenommen. In der Karte: MAC-Filter-Chip und
  Pairing-Button, während des Pairings „Pairing bis HH:MM“. Details unter
  [MAC-Filter und Pairing](#mac-filter-und-pairing).
- **Neu: Repeater als eigene Geräte.** Jeder AVM-Repeater bekommt ein eigenes Gerät (hängt an der
  FRITZ!Box) mit *Verbunden*-Status und – bei aktivierter FRITZ!Box-Steuerung – einem
  *Neustart*-Button, der den Repeater direkt über dessen TR-064 neu startet. Neue Option
  *Repeater als eigene Geräte anlegen* (standardmäßig an). Details unter
  [Repeater als eigene Geräte](#repeater-als-eigene-geräte).
- **Neu: Standardfilter der Karte ist jetzt *Aktiv*** (vorher *Alle*). Gilt für alle Karten, in
  denen `default_filter` nicht ausdrücklich gesetzt ist; wer weiter mit *Alle* starten möchte,
  wählt es im Editor oder setzt `default_filter: alle`.

**Behoben**

- **Der Button *Neu verbinden* schlug mit `UPnPError: errorCode: 606` fehl** (der *Neustart* ging
  dabei). Ursache: `FritzConnection.reconnect()` ruft den UPnP-Dienst `WANIPConn1` auf; diesen
  lehnen manche FRITZ!Boxen mit 606 („nicht autorisiert“) ab, obwohl das Konto berechtigt ist.
  Der bisherige Rückfall auf PPPoE griff nie, weil er nur bei einem *fehlenden* Dienst ansprang,
  nicht bei einem abgelehnten. Jetzt werden nacheinander die TR-064-Dienste `WANIPConnection1`
  und `WANPPPConnection1` (mit der Anmeldung der Integration) und erst danach die UPnP-Dienste
  versucht. Schlägt alles fehl, nennt die Meldung die Ursache und was zu prüfen ist. Alle
  Fehlermeldungen der Buttons sind jetzt übersetzt (de/en/nl).
- **Einheit „Geräte“ war nicht übersetzt.** Die drei Zähler-Sensoren trugen die Einheit fest auf
  Deutsch. Sie kommt jetzt aus den Übersetzungen: *Geräte* / *devices* / *apparaten*. Hinweis
  zur einmaligen Statistik-Meldung siehe [Fehlerbehebung](#fehlerbehebung).
- **Die Zeile *Anwesenheit* fehlte im Detail-Popup immer.** Die in 1.5.0 eingeführte Verlinkung
  zum `device_tracker` eines Geräts hat nie funktioniert: Home Assistants `ScannerEntity`
  überschreibt die `unique_id` fest mit der MAC-Adresse, das eigene `_attr_unique_id` der
  Integration (`<entry_id>_track_<mac>`) kam also nie in der Entitätsregistrierung an. Gesucht
  wurde aber genau danach – die Zuordnung blieb dadurch immer leer, und die Karte ließ die Zeile
  kommentarlos weg. Die Auflösung erfolgt jetzt über die MAC-Adresse (mit dem alten Schlüssel
  als Rückfallweg); die `unique_id` des Trackers wird zusätzlich explizit auf denselben Wert
  gesetzt, damit beide Wege übereinstimmen. Bestehende Tracker-Entitäten bleiben unverändert
  erhalten – es entstehen keine Duplikate.
- **Die Zeile *Anwesenheit* ist jetzt immer sichtbar** und sagt, was los ist, statt zu
  verschwinden: *zuhause* / *abwesend* (verlinkt auf die Entität), *Entität deaktiviert* (falls
  die Tracker-Entität in Home Assistant ausgeschaltet ist), *nicht aktiviert* (falls der Device
  Tracker in den Integrationseinstellungen gar nicht eingeschaltet ist – der Tooltip nennt den
  Weg dorthin) oder „—“, wenn es für dieses Gerät keinen Tracker gibt. Der angezeigte Zustand
  kommt jetzt aus der Tracker-Entität selbst, nicht mehr aus dem Aktiv-Status der FRITZ!Box.
- **Karte: automatische Sensor-Auswahl** beim Anlegen erkennt den Sammelsensor jetzt am Attribut
  `hosts` statt am Namen `…_gerate`; bei englischer oder niederländischer Home-Assistant-Sprache
  (`…_devices`, `…_apparaten`) wurde er bisher nicht gefunden.
- **Die Karte meldete sich in der Browser-Konsole weiterhin als 1.5.0.** Die Versionskennung in
  der Kartendatei war beim Release 1.5.1 nicht mitgezogen worden. Auf die Cache-Invalidierung
  hatte das keinen Einfluss – die läuft über den Parameter `?v=` an der Ressourcen-URL.

**Zur Warnung `The deprecated alias ScannerEntity was used from fritzbox_netzwerk`:** sie stammt
aus Version 1.5.0 und älter und ist seit 1.5.1 behoben (der Import erfolgt aus
`homeassistant.components.device_tracker`). Gegen den Quellcode von Home Assistant 2026.9.3
geprüft: weder Tracker noch übrige Module greifen auf einen veralteten Alias zu. Wer sie
weiterhin sieht, hat noch eine ältere Version geladen – bitte Version prüfen und Home Assistant
neu starten.

**Nicht an echter Hardware getestet.** MAC-Filter/Pairing, Repeater-Neustart und der
Sammel-Neustart wurden mit einer simulierten FRITZ!Box und Repeatern geprüft, nicht an echten
Geräten. Rückmeldungen bitte als GitHub-Issue.

### 1.5.1 – Deprecation-Warnung im Protokoll beseitigt

- **Behoben: Warnung `The deprecated alias ScannerEntity was used from fritzbox_netzwerk`.**
  Der Device Tracker importierte `ScannerEntity` aus
  `homeassistant.components.device_tracker.config_entry`. Seit Home Assistant 2026.6 ist das
  dort nur noch ein veralteter Alias (entfällt in HA Core 2027.6), der bei jedem Start eine
  Warnung ins Protokoll schreibt. Der Import erfolgt jetzt direkt aus
  `homeassistant.components.device_tracker` – diesen Pfad gibt es bereits seit Home Assistant
  2023.1, ältere Installationen sind also nicht betroffen. Rein funktional ändert sich nichts:
  Entitäten, entity_ids und Zustände der Tracker bleiben unverändert.
- **Vorsorglich mit umgestellt:** `EntityCategory` wird in `button.py` und `switch.py` jetzt aus
  `homeassistant.const` statt aus `homeassistant.helpers.entity` importiert. Das erzeugt heute
  noch keine Warnung, ist aber derselbe Fall – ein Alias am alten Ort.

### 1.5.0 – IP-Typ ehrlicher, kompakte Darstellung, Standardfilter

- **IP-Typ zeigt jetzt „fest" bzw. „dynamisch" statt „DHCP/statisch".** Die FRITZ!Box meldet
  auch eine dauerhaft zugewiesene IPv4 als „DHCP" – nur die Lease-Restzeit unterscheidet
  wirklich. Die Spalte klassifiziert daher anhand der Lease: aus dem Pool zugewiesen
  (Lease läuft ab) = *dynamisch*, sonst *fest*. Das ist die Angabe, die zählt.
- **Geräte ohne IP-Adresse** (einfache Switches, Powerline-Adapter, Mesh-Master) werden
  nicht mehr fälschlich als „statisch" angezeigt, sondern als „—".
- **Kompakter Modus** kürzt platzsparend: IP-Typ als „fest" / „dyn. 10", Tempo als „866 M" /
  „1 G" (die volle Angabe steht im Tooltip). Damit bleibt jede Zeile einzeilig.
- **Standardfilter wählbar.** Über *Standardfilter beim Laden* lässt sich festlegen, welcher
  Filter beim Laden oder Neuöffnen aktiv ist (z. B. „Aktiv"). Nach einem Refresh landet man
  nicht mehr zwangsläufig auf „Alle".
- **Device Tracker (optional).** In den Integrationseinstellungen aktivierbar: erzeugt pro
  Netzwerkgerät einen `device_tracker` (zuhause/abwesend) für Anwesenheit und Automationen.
  Neu auftauchende Geräte werden automatisch ergänzt. Standardmäßig aus, um bei großen Netzen
  nicht ungefragt viele Entitäten anzulegen.
- **FRITZ!Box-Steuerung (optional, experimentell).** In den Integrationseinstellungen
  aktivierbar: Schalter für die WLAN-Bänder (2,4 GHz, 5 GHz, Gast) sowie Buttons zum
  Neuverbinden (neue IP) und Neustarten der FRITZ!Box. Verfügbarkeit und Zuordnung der Bänder
  hängen vom Modell ab, daher experimentell; standardmäßig aus.
- **Steuerungsleiste in der Karte.** Über den Editor-Schalter *Steuerungsleiste anzeigen*
  blendet die Karte eine eigene Kategorie ein: Live-Download/-Upload sowie – wenn die
  FRITZ!Box-Steuerung aktiviert ist – die WLAN-Schalter und die Buttons Neuverbinden/Neustart
  (Neustart mit Zwei-Klick-Bestätigung).
- **Einzeln färbbare Kategorie-Symbole** (einheitlich mit *FRITZ!Box Anrufe*). Im Farbbereich
  des Editors lässt sich die Symbolfarbe jeder Kategorie (Alle, Aktiv, Inaktiv, Gast,
  Gesperrt, Update) getrennt einstellen. Die Chips sind wie bisher einzeln ein-/ausblendbar.
- **Tabs (Kategorien) in der Karte.** Über den Editor-Schalter *Kategorien als Tabs anzeigen*
  bekommt die Karte oben Reiter: **Netzwerk** und – wenn die Steuerungsleiste aktiviert ist –
  **Steuerung**. Die Reiter trennen sauber: *Netzwerk* zeigt ausschließlich Filterleiste,
  Suchfeld, Zusammenfassung und Geräteliste, *Steuerung* ausschließlich die Down/Up-Anzeige,
  die WLAN-Schalter und die Buttons Neuverbinden/Neustart. Es erscheint nichts doppelt. Der
  Steuerungs-Reiter wird nur angelegt, wenn es etwas zu steuern gibt. Sind die Tabs
  ausgeschaltet (Standard), erscheinen wie bisher beide Bereiche untereinander in einer
  einzigen Ansicht.
- **Device-Tracker im Detail-Popup.** Ist der Device Tracker aktiviert, zeigt das Popup eines
  Geräts eine Zeile *Anwesenheit* mit Link direkt zur Tracker-Entität – statt einer
  redundanten eigenen Übersichtsseite.

### 1.4.2 – Absturz bei ungewöhnlichen Geräte-Identifiern behoben

- **Behoben: Absturz beim Datenabruf** (`too many values to unpack (expected 2, got 3)`). Die
  Geräte-Zuordnung ging davon aus, dass Verbindungen und Identifier in der
  Home-Assistant-Geräteregistrierung immer 2-Tupel `(domain, id)` sind. Einige Integrationen
  (z. B. SunSpec/Fronius) legen ihre Identifier aber als 3-Tupel an, worauf das feste Entpacken
  abstürzte – und weil dabei die gesamte Aktualisierung scheiterte, funktionierte die
  Integration auf betroffenen Systemen gar nicht. Verbindungen und Identifier werden jetzt
  tolerant gegenüber abweichenden Tupellängen ausgewertet: Jedes enthaltene Textelement kommt
  als MAC-Kandidat in Frage, alles andere wird verworfen. Kein Absturz mehr.

### 1.4.1 – Absturz der Geräte-Zuordnung behoben, Editor übersetzt

- **Karten-Editor mehrsprachig.** Auch die Konfigurationsoberfläche der Karte (Feldnamen,
  Hilfetexte, Gruppentitel, Farbbereich) folgt jetzt der Home-Assistant-Sprache – Deutsch,
  Englisch und Niederländisch.
- **Behoben: Absturz beim Datenabruf** (`'str' object has no attribute 'connections'`). Die in
  1.4.0 geänderte Iteration der Geräteregistrierung funktionierte nur auf Home Assistant
  2026.9+, wo `for device in registry.devices` die Geräte-Einträge liefert. Auf älteren
  Versionen liefert dieselbe Iteration die Schlüssel (Strings), was zum Absturz führte – und
  weil dabei die gesamte Aktualisierung scheiterte, wurden **gar keine** Home-Assistant-Namen
  mehr zugeordnet. Die Iteration ist jetzt versionsübergreifend: Strings werden über die
  unterstützte Methode `async_get` aufgelöst. Kein Absturz, keine Deprecation-Warnung.

### 1.4.0 – Mehrsprachige Karte, robustere HA-Zuordnung

- **Verbindungs-Sensoren (Down/Up).** Vier neue Sensoren: aktuelle Download- und Upload-Rate
  (kB/s) sowie die maximalen Leitungs-Sync-Raten (Mbit/s). Fehlt der WAN-Dienst (Access-Point-
  Betrieb), bleiben die Sensoren „unbekannt", ohne die Geräteliste zu stören.

- **Karte mehrsprachig (Deutsch, Englisch, Niederländisch).** Alle Beschriftungen der Karte
  – Spaltentitel, Filter, Suchfeld, Zusammenfassung, Zellen und das Detail-Popup – folgen
  jetzt der in Home Assistant eingestellten Sprache. Im Editor lässt sich die Sprache über
  *Sprache der Karte* auch fest wählen.
- **HA-Geräte-Zuordnung robuster.** Die MAC-Adresse wird nun auch aus MAC-artigen Werten
  anderer Verbindungstypen und aus den Geräte-Identifiern gelesen, nicht nur aus Verbindungen
  vom Typ „mac". Die ungültige Null-MAC (00:00:…) wird ignoriert. Damit werden mehr Geräte
  zugeordnet, die ihre MAC an anderer Stelle hinterlegen.

  Grenze: Trägt eine Integration die MAC eines Geräts gar nicht in die Home-Assistant-
  Geräteregistrierung ein (bei manchen Matter-Geräten der Fall, die ihre MAC nur in den
  Matter-Diagnosedaten zeigen), kann es über diesen Weg nicht zugeordnet werden. Das liegt an
  der jeweiligen Quell-Integration. Home Assistant speichert die IP-Adresse nicht als
  Geräte-Kennung, daher ist eine Zuordnung über die IP nicht möglich.

### 1.3.1 – Installations-/Veröffentlichungsfix

- Kein funktionaler Unterschied zu 1.3.0. Diese Version stellt sicher, dass HACS die
  Integration sauber neu einliest (die Domain der Integration wird wieder korrekt erkannt).
  Falls HACS zuvor mit „custom_components/None/manifest.json" abbrach: Repository in HACS
  entfernen und erneut hinzufügen, dann 1.3.1 herunterladen.


### 1.3.0 – Verlinkter HA-Name, ausblendbare Filter, scrollbarer Datenbereich, Logo

- **HA-Gerätename verlinkt.** In der Spalte *Home Assistant* führt ein Klick auf den Namen
  direkt zum Gerät in Home Assistant. Zusammen mit dem Klick auf die IP (Weboberfläche)
  kommt man so ohne Umweg über das Detail-Popup ans Ziel.
- **Filter-Buttons einzeln ausblendbar.** Nicht benötigte Auswahl-Buttons (z. B. Gast,
  Gesperrt, Update) lassen sich im Editor einzeln abschalten.
- **Feststehender Kopf, scrollbarer Datenbereich.** Über *Sichtbare Zeilen, dann scrollen*
  lässt sich eine Zeilenzahl festlegen; darüber wird nur der Datenbereich gescrollt, während
  Titel, Auswahl und Tabellenüberschrift stehen bleiben.
- **Eigenes Logo.** Im Ordner `custom_components/fritzbox_netzwerk/brand/` liegt das
  Integrations-Logo (`icon.png`, `icon@2x.png`, `logo.png`, `logo@2x.png`) im Format von
  `home-assistant/brands`. Damit es in Home Assistant erscheint, müssen `icon.png` (256×256)
  und `icon@2x.png` (512×512) per Pull Request bei
  [home-assistant/brands](https://github.com/home-assistant/brands) unter
  `custom_integrations/fritzbox_netzwerk/` eingereicht werden.
- **Niederländische Übersetzung** ergänzt; die Integration spricht jetzt Deutsch, Englisch
  und Niederländisch.
- **Fehler behoben: Deprecation-Warnung im Protokoll.** Der Zugriff auf die
  Geräteregistrierung nutzte `registry.devices.values()`, was Home Assistant als veraltet
  markiert (Entfernung in 2027.9). Jetzt wird `registry.devices` direkt iteriert.
- **Fehler behoben: HA-Namen fehlten teils.** Deaktivierte Home-Assistant-Geräte wurden bei
  der MAC-Zuordnung übersprungen; dadurch blieb die HA-Spalte bei manchen Geräten leer,
  obwohl ein passendes HA-Gerät mit MAC vorhanden war. Solche Geräte werden jetzt
  berücksichtigt.

### 1.2.1 – Fehlerbehebungen

- **Große Netze (viele Geräte).** Die Karte hat den Tabellenkörper bei jeder
  Zustandsänderung in Home Assistant neu aufgebaut – bei rund 160 Geräten trieb das CPU und
  Speicher massiv nach oben und ließ den Browser einfrieren. Jetzt wird nur noch neu
  gezeichnet, wenn sich die Gerätedaten tatsächlich geändert haben.
- **500-Fehler beim Speichern der Integrationseinstellungen.** Der Options-Dialog nutzte
  gleichzeitig `OptionsFlowWithReload` und einen eigenen Update-Listener, was aktuelle
  Home-Assistant-Versionen mit einem Fehler quittieren. Der zusätzliche Listener wurde
  entfernt; das Neuladen übernimmt weiterhin `OptionsFlowWithReload`.

### 1.2.0 – Zuletzt online, Internetzugang schalten, Titel ausblendbar

- Neue Spalte **Zuletzt online** (standardmäßig aus). Die FRITZ!Box liefert diesen
  Zeitstempel nicht – die Integration schreibt ihn ab Installation selbst mit und speichert
  ihn dauerhaft, sodass er Neustarts übersteht. Anzeige relativ („vor 3 min", „gestern")
  bzw. als Datum, aktive Geräte zeigen „jetzt online".
- Neuer Dienst **`set_internet_access`** (MAC + an/aus) zum Sperren/Freigeben des
  Internetzugangs über TR-064, plus ein Schalter im Detail-Popup. Experimentell, da je nach
  FRITZ!OS/Modell verfügbar.
- **Titel ausblendbar** über den Editor-Schalter *Titel anzeigen* – praktisch für ein
  Popup oder eine kompakte Ansicht.

### 1.1.0 – Blättern statt Spalten verstecken

- Auf schmalen Karten werden **keine Spalten mehr versteckt**. Stattdessen wird die Tabelle
  waagerecht scrollbar – die zuvor auf dem Smartphone fehlende Spalte *Home Assistant* (und
  alle weiteren) ist damit wieder erreichbar.
- **Blätter-Pfeile** am linken und rechten Rand, zusätzlich zum Wischen mit dem Finger. Sie
  erscheinen nur, wenn in ihre Richtung noch etwas verborgen ist.
- **Statuspunkt und Gerätename bleiben beim Blättern stehen** (fixierte Spalten).
- Ersetzt das Kategorie-Wischen aus 1.0.0, das die eigentliche Ursache – ausgeblendete
  Spalten auf dem Telefon – nicht behob.
- Neue Schalter *Blätter-Pfeile bei breiter Tabelle* und *Gerätename beim Blättern
  festhalten* (der frühere *Wischen wechselt die Kategorie* entfällt).

### 1.0.0 – Erste stabile Version

- **Wischgeste** auf schmalen Karten: nach links oder rechts zwischen den Kategorien
  blättern (Smartphone)
- **Klick auf die IP-Adresse** öffnet die Weboberfläche des Geräts im Browser; im Popup
  zusätzlich der Knopf *Weboberfläche öffnen*
- Icons an die Schwester-Integration *FRITZ!Box Anrufe* angeglichen (Farben-Sektion
  `mdi:palette-outline`, Zurücksetzen `mdi:restore`, sowie die geteilten Symbole
  `mdi:close`, `mdi:check`, `mdi:chevron-down`, `mdi:table-column`)
- Neue Schalter: *Wischen wechselt die Kategorie*, *Klick auf die IP öffnet die
  Weboberfläche*, *Notfalls http://IP verwenden*

### 0.2.0 – Detail-Popup

- Klick oder Enter auf eine Zeile öffnet ein Popup mit allen Feldern des Geräts,
  einschließlich der MAC-Adresse, die auf schmalen Karten in der Tabelle ausgeblendet wird
- Kopier-Knöpfe für IP- und MAC-Adresse
- Aktionen im Popup: *In Home Assistant öffnen* und *Aufwecken (WoL)*
- Zeilen sind jetzt per Tastatur erreichbar (Tab, Enter)
- Neuer Schalter *Klick öffnet ein Detail-Popup* (Standard: an). Ist er aus, gilt wieder
  das bisherige Verhalten des Schalters *Klick öffnet das Home-Assistant-Gerät*

### 0.1.0 – Erstveröffentlichung

- Integration mit Einrichtungsdialog, erneuter Anmeldung und Options-Flow
- Sammelsensor mit vollständiger Geräteliste plus zwei Zähler-Sensoren
- Dashboard-Karte mit Sortierung, Suche, Filterleiste, zwölf Spalten und Farbeditor
- IP-Typ-Erfassung in eigenem, langsamerem Takt
- Dienste `set_device_name` und `wake_on_lan`

---

## Lizenz

MIT
