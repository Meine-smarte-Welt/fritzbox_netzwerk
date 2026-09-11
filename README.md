# FRITZ!Box Netzwerk

Eine Home-Assistant-Integration, die alle Geräte im FRITZ!Box-Heimnetz als sortierbare
Tabelle auf das Dashboard bringt – mit IP-Adresse, MAC-Adresse, Verbindungsart und dem
passenden Home-Assistant-Gerätenamen.

![Version](https://img.shields.io/badge/Version-1.3.0-blue)
![HACS](https://img.shields.io/badge/HACS-Custom-orange)

---

## Inhalt

- [Was die Integration kann](#was-die-integration-kann)
- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Einrichtung](#einrichtung)
- [Einstellungen](#einstellungen)
- [Sensoren](#sensoren)
- [Dashboard-Karte](#dashboard-karte)
  - [Spalten](#spalten)
  - [Sortieren, filtern, suchen](#sortieren-filtern-suchen)
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

Das Attribut `hosts` ist per `_unrecorded_attributes` vom Recorder ausgenommen. Ohne das
schriebe Home Assistant die vollständige Geräteliste bei jeder Änderung in die Datenbank –
bei 60 Geräten rund 15–20 kB pro Eintrag.

Weitere Attribute am Hauptsensor: `gesamt`, `aktiv`, `inaktiv`, `gastnetz`, `gesperrt`,
`updates_verfuegbar`, `statische_ip`, `letzte_abfrage`, `letzte_ip_typ_abfrage`.

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

Suchfeld und Filterleiste arbeiten zusammen: „Aktiv" plus Suchbegriff zeigt nur verbundene
Geräte, auf die der Begriff passt. Beide Bedienelemente behalten ihren Inhalt, wenn der
Sensor im Hintergrund neue Daten liefert.

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

---

## Fehlerbehebung

**Die Einrichtung meldet „Das Konto hat keinen Zugriff auf die FRITZ!Box-Einstellungen".**
In der FRITZ!Box unter System → FRITZ!Box-Benutzer beim verwendeten Konto die Berechtigung
*FRITZ!Box Einstellungen* setzen. Ein reiner Benutzer ohne diese Berechtigung kann die
Geräteliste nicht abrufen.

**Die Einrichtung meldet, der Dienst „Hosts" fehle.**
Unter Heimnetz → Netzwerk → Netzwerkeinstellungen die Option *Zugriff für Anwendungen
zulassen* aktivieren. Ohne sie ist die TR-064-Schnittstelle komplett abgeschaltet.

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

Die Integration ist auf **Deutsch**, **Englisch** und **Niederländisch** übersetzt
(`de`, `en`, `nl`). Home Assistant wählt automatisch anhand der eingestellten Sprache.

---

## Bekannte Einschränkungen

- **Statische IP-Adressen lassen sich nicht ändern.** Die TR-064-Schnittstelle von AVM
  kennt dafür keine Aktion. Schreibbar sind dort nur Gerätename, Anzeigename,
  Wake-on-LAN, Echtzeitpriorität und Geräteklasse. Ein Setzen der IP-Adresse wäre nur über
  die Weboberfläche der FRITZ!Box möglich – undokumentiert und bei jedem FRITZ!OS-Update
  potenziell defekt. Das ist bewusst nicht Teil dieser Version.
- **Kein Mesh.** WLAN-Band, Signalstärke und der Repeater, an dem ein Gerät hängt, stehen
  in einer eigenen Schnittstelle (`X_AVM-DE_GetMeshListPath`) und sind noch nicht
  ausgewertet.
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
python3 tests/test_hosts.py     # 35 Fälle
node tests/test_card.js         # 125 Fälle, jsdom gegen die echte Kartendatei
```

Die JS-Tests laden die ausgelieferte `fritzbox-netzwerk-card.js` unverändert in ein echtes
DOM und steuern die Karte genau so an, wie Lovelace es tut – über `setConfig()`, den
`hass`-Setter und echte Klick- und Tastaturereignisse. Es gibt keine zweite Kopie des
Kartencodes im Testaufbau.

---

## Versionshistorie

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
