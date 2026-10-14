🇩🇪 [Deutsch](README.md) · [🇬🇧 English](README.en.md) · 🇳🇱 Nederlands

# FRITZ!Box Netzwerk

Een Home Assistant-integratie die alle apparaten in het FRITZ!Box-thuisnetwerk als sorteerbare tabel op het dashboard zet – met IP-adres, MAC-adres, verbindingstype en de bijbehorende Home Assistant-apparaatnaam.

![Version](https://img.shields.io/badge/Version-1.9.0-blue)
![HACS](https://img.shields.io/badge/HACS-Custom-orange)

> Dit is de Nederlandse uitgave. De Duitse [README.md](README.md) is het hoofdbestand en bevat de volledige kaartreferentie, het hoofdstuk probleemoplossing en de complete versiegeschiedenis. Onderdelen met „alleen Duits” zijn nog niet vertaald.

---

## Inhoud

- [Functies](#functies)
- [Vereisten](#vereisten)
- [Installatie](#installatie)
- [Instellen](#instellen)
- [Instellingen](#instellingen)
- [Sensoren](#sensoren)
- [Gebeurtenissen](#gebeurtenissen)
- [Mesh en repeaters](#mesh-en-repeaters)
- [MAC-filter en pairing](#mac-filter-en-pairing)
- [Ouderlijk toezicht: toegangsprofielen (experimenteel)](#ouderlijk-toezicht-toegangsprofielen-experimenteel)
- [CPU en RAM van de box (experimenteel)](#cpu-en-ram-van-de-box-experimenteel)
- [DNS-instellingen (experimenteel)](#dns-instellingen-experimenteel)
- [Statisch IP-adres (experimenteel)](#statisch-ip-adres-experimenteel)
- [De dashboardkaart](#de-dashboardkaart)
- [Services](#services)
- [Blueprints](#blueprints)
- [Versieweergave en updatemelding](#versieweergave-en-updatemelding)
- [Talen](#talen)
- [Beveiliging](#beveiliging)
- [Bekende beperkingen](#bekende-beperkingen)
- [Probleemoplossing](#probleemoplossing)
- [Bestandsintegriteit](#bestandsintegriteit)
- [Ontwikkeling en tests](#ontwikkeling-en-tests)
- [Versiegeschiedenis](#versiegeschiedenis)
- [Licentie](#licentie)

---

## Functies

- Alle bekende netwerkapparaten van de FRITZ!Box als **één** tabel op het dashboard
- **Sorteerbaar** door op een kolomkop te klikken, ook met het toetsenbord; **zoeken** op naam, IP, MAC, model en Home Assistant-naam
- **Filterbalk**: Alle, Actief, Inactief, Gast, Geblokkeerd, Update, Vast IP – elke knop afzonderlijk te verbergen
- **Wifi-band** (2,4 / 5 GHz), **fabrikant bij het MAC-adres** (meegeleverde lijst, geen internet nodig), **MAC met één klik kopiëren**
- **IP-filter met jokertekens** (`192.168.2.*`) om een groot netwerk over meerdere kaarten te verdelen
- **Detailvenster** per apparaat met alle velden, Wake-on-LAN, naam wijzigen, label/notitie/„gereserveerd”-markering en een sprong naar het Home Assistant-apparaat
- **Laatst gezien**, **internettoegang schakelen** (experimenteel), **IP-type** (vast of dynamisch)
- **Verbindingssensoren** (download-/uploadsnelheid, lijnsnelheid, extern IP, online-tijd, verbindingsstatus) en **gebeurtenissen** („nieuw apparaat”, „extern IP gewijzigd”)
- **Meshgroep**: FRITZ!Box en repeaters als één eenheid, knop „Alle FRITZ!-apparaten herstarten”
- **Wifi-MAC-filter** aan/uit en tijdelijk vrijgeven („pairing”)
- **Ouderlijk toezicht** (experimenteel): toegangsprofielen per apparaat wisselen, ook tijdelijk
- **DNS-instellingen** van de box (experimenteel, sinds 1.8.0): lezen en wijzigen
- **Statisch IP-adres** per apparaat (experimenteel, sinds 1.8.0): toewijzen met controle op dubbele adressen, knop in het detailvenster
- **Versieweergave en updatemelding** op de besturingspagina van de kaart
- Volledig instelbaar via de interface incl. **vrij te kiezen kleuren**, drie talen (de, en, nl)

De kaart wordt met de integratie meegeleverd en automatisch als Lovelace-resource geregistreerd.

---

## Vereisten

- Home Assistant 2024.11 of nieuwer
- Een FRITZ!Box met **„Toegang voor toepassingen toestaan”** ingeschakeld (Thuisnetwerk → Netwerk → Netwerkinstellingen)
- Een FRITZ!Box-gebruiker met het recht **„FRITZ!Box-instellingen”**

---

## Installatie

### Via HACS (aanbevolen)

1. HACS → Integraties → menu rechtsboven → **Aangepaste repositories**
2. Voeg `https://github.com/Meine-smarte-Welt/fritzbox_netzwerk` toe als categorie *Integratie*
3. Installeer „FRITZ!Box Netzwerk”
4. Herstart Home Assistant

### Handmatig

Kopieer de map `custom_components/fritzbox_netzwerk` naar de map `config` van Home Assistant en herstart.

---

## Instellen

Instellingen → Apparaten & diensten → **Integratie toevoegen** → „FRITZ!Box Netzwerk”.

| Veld | Betekenis |
| --- | --- |
| Adres | Hostnaam of IP-adres, meestal `fritz.box` |
| Gebruikersnaam | FRITZ!Box-gebruiker met het recht „FRITZ!Box-instellingen” |
| Wachtwoord | Het bijbehorende wachtwoord |
| Versleutelde verbinding | HTTPS in plaats van HTTP naar de FRITZ!Box |
| Poort | `0` gebruikt de standaardpoorten; of vul een eigen poort in |
| Toegang op afstand via MyFRITZ!/HTTPS | Gebruikt HTTPS en het TR-064-padvoorvoegsel `/tr064` |

De gegevens worden direct gecontroleerd (bereikbaar, aanmelding geldig, hosts-service bruikbaar). Mislukt een van de drie, dan noemt het dialoogvenster de concrete oorzaak.

Voor toegang op afstand vul je het MyFRITZ!- of DynDNS-adres **zonder protocol, poort en pad** in, vul je de HTTPS-poort apart in en schakel je „Toegang op afstand via MyFRITZ!/HTTPS” in. **Let op:** `fritzconnection` controleert het TLS-certificaat niet; via het open internet is een VPN naar de eigen FRITZ!Box de veiligere keuze (details in de Duitse README).

---

## Instellingen

Via *Configureren* bij de integratie:

| Instelling | Standaard | Betekenis |
| --- | --- | --- |
| Ophaalinterval | 60 s | Hoe vaak de apparatenlijst wordt opgehaald (30–3600 s) |
| IP-type vastleggen | aan | Of DHCP/statisch wordt bepaald |
| Interval IP-type | 15 min | Cyclus van de IP-typebepaling |
| Wifi-band per apparaat vastleggen | aan | Leest per wifi-netwerk de verbonden apparaten, zodat de kaart de band kan tonen |
| Apparaattrackers aanmaken | uit | Eén `device_tracker` per netwerkapparaat |
| Repeaters als eigen apparaten aanmaken | aan | Eén Home Assistant-apparaat per AVM-repeater, meshsensor, knop „Alles herstarten” |
| FRITZ!Box-besturing (experimenteel) | uit | Wifi-schakelaar, MAC-filterschakelaar, pairingknop, knoppen voor opnieuw verbinden/herstarten |
| Dagelijks op nieuwe versie controleren | aan | Vraagt eenmaal per dag bij GitHub naar de nieuwste versie; er worden geen gegevens over jou of de box verzonden |
| Toegangsprofielen van ouderlijk toezicht besturen (experimenteel) | uit | Schakelt de services en de profielkeuze in het detailvenster in |
| DNS-instellingen van de box wijzigen (experimenteel) | uit | Staat `set_dns_settings` toe te schrijven; lezen en voorvertoning werken altijd |
| Statisch IP-adres instellen (experimenteel) | uit | Staat `set_static_ip` en de kaartknop toe te schrijven; de voorvertoning (`dry_run`) werkt altijd |
| CPU en RAM van de box lezen (experimenteel) | uit | Drie sensoren uit de webinterface van de box |
| Netwerkapparaten als eigen apparaten aanmaken | uit | Eén HA-apparaat per geselecteerd apparaat, selectie via patroon |
| Pairingduur | 5 min | Hoe lang het MAC-filter bij pairing uit blijft (1–120 min) |

---

## Sensoren

| Sensor | Status | Doel |
| --- | --- | --- |
| `sensor.<name>_gerate` | Aantal verbonden apparaten | Bevat de volledige apparatenlijst in het attribuut `hosts`; gegevensbron van de kaart |
| `sensor.<name>_gerate_mit_update` | Aantal | Automatisering „nieuwe firmware beschikbaar” |
| `sensor.<name>_gesperrte_gerate` | Aantal | Bewaking van ouderlijk toezicht |
| `sensor.<name>_download` / `_upload` | kB/s | Actuele overdrachtssnelheid |
| `sensor.<name>_mesh` | Aantal online | Bereikbare FRITZ!-apparaten (box + repeaters); alleen met repeaters |
| `sensor.<name>_download_leitungsrate` / `_upload_leitungsrate` | Mbit/s | Maximale lijnsnelheid (sync) |
| `sensor.<name>_externe_ip` | IPv4-adres | Actueel publiek IP |
| `sensor.<name>_online_seit` | Tijdstempel | Sinds wanneer de verbinding actief is |
| `binary_sensor.<name>_internet_verbunden` | Verbonden/Niet verbonden | Is de box online? |

Ontbreekt de WAN-service (bijv. als de box alleen als access point draait), dan blijven deze sensoren „onbekend” zonder de apparatenlijst te beïnvloeden. Het attribuut `hosts` is van de recorder uitgesloten.

## Gebeurtenissen

Sinds 1.6.2: „nieuw apparaat” bij het eerste verschijnen in het thuisnetwerk en „extern IP gewijzigd”, bruikbaar in automatiseringen zonder extra TR-064-aanroepen.

---

## Mesh en repeaters

De FRITZ!Box en de AVM-repeaters vormen samen het mesh. De integratie behandelt ze als **één groep**: repeaters verschijnen als eigen apparaten onder de box, er is een online-teller en de knop „Alle FRITZ!-apparaten herstarten” (eerst repeaters, de box als laatste). Sinds 1.6.3 toont de kaart bij „Verbonden via” welke meshbuur een apparaat gebruikt, met de verbindingssnelheid. Geen signaalsterkte in dBm (de meshlijst levert die niet). Sinds 1.9.0 geldt een apparaat ook als repeater als de mesh-topologie van de box het als meshlid vermeldt, wordt de wifi-band van apparaten achter een repeater uit de naam van de mesh-interface gelezen (beide aannames niet op echte hardware getest), worden repeaters met alleen een wachtwoord (zonder gebruikersnaam) opnieuw met een lege gebruikersnaam geprobeerd en kan de lijst op mesh-verbinding worden gegroepeerd (`group_by: mesh`). Details: Duitse README.

## MAC-filter en pairing

Met *FRITZ!Box-besturing* ingeschakeld krijg je `switch.<name>_mac_filter` (permanent aan/uit) en `button.<name>_pairing_starten` (filter voor de ingestelde tijd uit, daarna **automatisch weer aan**). De services `set_mac_filter` en `start_pairing` doen hetzelfde vanuit automatiseringen. Experimenteel.

## Ouderlijk toezicht: toegangsprofielen (experimenteel)

De integratie **wisselt tussen bestaande toegangsprofielen** (Internet → Filters → Toegangsprofielen); aanmaken en bewerken doe je nog steeds in de FRITZ!Box. Schakel de optie in en gebruik de rij **Toegangsprofiel** in het detailvenster of de services `list_access_profiles`, `get_access_profile`, `set_access_profile`. Met een aantal minuten geldt het profiel maar zo lang, daarna wordt het vorige hersteld. De rij is te verbergen met `show_parental: false`. Gebruikt de ongedocumenteerde webinterface, geen TR-064.

## CPU en RAM van de box (experimenteel)

De optie „CPU en RAM van de box lezen (experimenteel)” (standaard uit) maakt drie sensoren aan: CPU-belasting, RAM-belasting, CPU-temperatuur. Ze komen uit de webinterfacepagina `ecoStat`, niet uit TR-064; op geen enkele box getest – vergelijk met Systeem → Energiemonitor.

---

## DNS-instellingen (experimenteel)

Sinds 1.8.0 leest de integratie de DNS-instellingen van de FRITZ!Box en kan ze – alleen na het inschakelen van de optie – wijzigen.

| Plek in de FRITZ!Box | Serviceveld |
| --- | --- |
| Internet → Accountgegevens → DNS-server (IPv4) | `internet_ipv4_custom`, `internet_ipv4_dns1`, `internet_ipv4_dns2` |
| Internet → Accountgegevens → DNS-server (IPv6) | `internet_ipv6_custom`, `internet_ipv6_dns1`, `internet_ipv6_dns2` |
| Thuisnetwerk → Netwerk → Netwerkinstellingen → Uitgebreid → IPv4 | `home_ipv4_dns` |
| Thuisnetwerk → Netwerk → Netwerkinstellingen → Uitgebreid → IPv6 | `home_ipv6_dns`, `home_ipv6_advertise` |

- `fritzbox_netzwerk.get_dns_settings` leest alleen en geeft de waarden als antwoord terug.
- `fritzbox_netzwerk.set_dns_settings` wijzigt alleen de opgegeven velden. Adressen worden gecontroleerd, de box wordt eerst gelezen, na het schrijven gecontroleerd en bij afwijking wordt de vorige toestand hersteld. Vraagt de box om een tweefactorbevestiging, dan wordt niets gewijzigd.
- `dry_run: true` toont wat er zou veranderen en werkt ook zonder de optie.

**Teststatus (eerlijk):** de opbouw van de antwoorden `dnscfg` en `ipv6`, de aanmelding en de schrijfwijze zijn op een FRITZ!Box 5690 Pro alleen **gelezen**. **Schrijven is op geen enkele echte box getest.** De REST-interface (`/api/v0/generic/…`) is niet gedocumenteerd door AVM, geen TR-064 en kan met FRITZ!OS veranderen. Verkeerde DNS-servers kunnen de naamresolutie in het hele thuisnetwerk verstoren – noteer eerst de waarden.

## Statisch IP-adres (experimenteel)

Sinds 1.8.0 kan de integratie een apparaat een vast IPv4-adres toewijzen – dit komt overeen met *Thuisnetwerk → Netwerk → apparaat bewerken → „Dit netwerkapparaat altijd hetzelfde IPv4-adres geven”*. Schakel de optie „Statisch IP-adres instellen (experimenteel)” in.

- **Service:** `fritzbox_netzwerk.set_static_ip` met `mac`, `ip` en optioneel `dry_run: true` (voorvertoning, werkt ook zonder de optie).
- **Knop in de kaart:** in het detailvenster de rij „Statisch IP” → *Instellen* → adres invullen → *Controleren* (alleen controle) of *Toepassen*. Te verbergen met `show_static_ip: false`.
- **Geen dubbele adressen:** het verzoek wordt geweigerd als het adres van een ander actief, vast of als „gereserveerd” gemarkeerd apparaat is, het adres van de box zelf is, buiten het thuisnetwerk valt, een netwerk-/broadcastadres is of geen geldig apparaatadres. Een offline apparaat met hetzelfde adres en een adres binnen het DHCP-bereik geven alleen een waarschuwing.
- **Herstart nodig:** het nieuwe adres geldt pas nadat het apparaat is herstart of opnieuw met het netwerk is verbonden.
- **Vangnet:** ontbreken de verwachte velden in het antwoord van de box, dan wordt niets geschreven. Na het schrijven wordt de box opnieuw gelezen; bij afwijking wordt de vorige toestand hersteld. Het huidige toegangsprofiel wordt meegestuurd.

**Teststatus (eerlijk):** de controle op dubbele adressen is met tests gedekt. De **veldnamen van de webinterface** (`edit_device`) zijn **aangenomen** en op geen enkele box getest – niet gelezen en niet geschreven. Past de opbouw niet, dan meldt de service „niets gewijzigd”; open dan een issue met het verzoek dat de box bij het opslaan verstuurt (browser-ontwikkelaarstools → Netwerk).

---

## De dashboardkaart

De kaart wordt met de integratie meegeleverd (`custom:fritzbox-netzwerk-card`). Hij heeft een grafische editor; elke kolom, elk filter, de besturingsbalk en de rijen van het detailvenster zijn afzonderlijk aan of uit te zetten, kleuren zijn vrij te kiezen, drie talen. De volledige referentie (kolommen, sorteren, IP-filter, tabs, groeperen, CSV-export, gast-wifi-QR-code, vegen op telefoons, kleuren) staat in de Duitse README.

```yaml
type: custom:fritzbox-netzwerk-card
entity: sensor.fritz_box_5690_pro_netzwerk_gerate
title: Thuisnetwerk
show_title: true
show_status: true
show_name: true
show_ip: true
show_mac: true
show_connection: true
show_ha_name: true
show_ip_type: true
show_vendor: false
show_band: false
show_summary: true
show_search: true
show_filter: true
default_filter: aktiv   # alle | aktiv | inaktiv | gast | gesperrt | update | fest
ip_filter: ""           # bijv. "192.168.2.*"
show_parental: true     # rij toegangsprofiel in het detailvenster
show_static_ip: true    # rij statisch IP in het detailvenster
sort_by: ip
sort_dir: asc
```

---

## Services

Zijn er meerdere boxen ingesteld, dan accepteren alle services een optioneel veld `config_entry` dat de box kiest.

| Service | Doel |
| --- | --- |
| `set_device_name` | Een apparaat in de box hernoemen |
| `wake_on_lan` | Een apparaat wekken |
| `set_internet_access` (experimenteel) | Internettoegang van een apparaat blokkeren/toestaan |
| `set_mac_filter`, `start_pairing` (experimenteel) | Wifi-MAC-filter en tijdelijke pairing |
| `reboot_mesh` (experimenteel) | Repeaters en box herstarten |
| `gast_wlan_info` | Gast-wifigegevens (voor de QR-code); sinds 1.9.0 wordt de gastservice herkend en kan een optionele `service` (1-4) die afdwingen |
| `set_device_note` | Label, notitie en „gereserveerd”-markering (alleen in Home Assistant opgeslagen) |
| `mark_devices_reserved` | Veel apparaten tegelijk als „gereserveerd” markeren via IP-patroon (alleen in Home Assistant opgeslagen; `dry_run` toont een voorbeeld) |
| `list_access_profiles`, `get_access_profile`, `set_access_profile` (experimenteel) | Profielen van ouderlijk toezicht |
| `get_dns_settings`, `set_dns_settings` (experimenteel) | DNS-instellingen van de box |
| `set_static_ip` (experimenteel) | Vast IPv4-adres voor een apparaat |
| `install_blueprints`, `update_oui` | Blueprints installeren, fabrikantenlijst bijwerken |

## Blueprints

De integratie levert blueprints en een script mee; de knop „Blueprints installeren” kopieert ze naar je Home Assistant-configuratie. Details: Duitse README.

---

## Versieweergave en updatemelding

De geïnstalleerde versie staat in de kaart (tandwieltab → app-versie), in de kaarteditor en in het optiesdialoogvenster. Bestaat er op GitHub een nieuwere release (eenmaal per dag gecontroleerd), dan wordt die oranje gemarkeerd met een link naar de release-notities.

## Talen

Duits, Engels en Nederlands – in de config flow, entiteiten, services en de kaart (taal uit Home Assistant, terugval Engels).

## Beveiliging

Schrijfacties vereisen beheerdersrechten; invoer wordt in de backend gecontroleerd; teksten in de kaart worden geëscaped. Opties voor experimentele schrijffuncties staan **standaard uit** en riskante acties hebben waar mogelijk een voorvertoning (`dry_run`).

---

## Bekende beperkingen

- **„Alle ongebruikte verbindingen verwijderen” ontbreekt** – TR-064 heeft daarvoor geen actie.
- **Statisch IP en DNS schrijven zijn experimenteel** en gebruiken de ongedocumenteerde webinterface van de box. Schrijven is op geen enkele echte box getest; de veldnamen voor het statische IP zijn aangenomen. Ze kunnen met elke FRITZ!OS-update breken.
- **Mesh maar gedeeltelijk:** geen signaalsterkte in dBm.
- **Dataverbruik per apparaat** levert de box niet via TR-064.
- Apparaten worden uitsluitend via het MAC-adres aan Home Assistant-apparaten gekoppeld.
- De volledige lijst staat in de Duitse README.

## Probleemoplossing

Alleen Duits: zie het hoofdstuk „Fehlerbehebung” in [README.md](README.md#fehlerbehebung). Logger: `custom_components.fritzbox_netzwerk`; de diagnose-download is geanonimiseerd.

## Bestandsintegriteit

Elk `.py`-, `.js`- en `.yaml`-bestand begint met een SHA-256-header over de inhoud (vanaf regel 2). Controleren met `tail -n +2 bestand.py | sha256sum`. De hashes van de JSON-bestanden staan in de Duitse [README.md](README.md#datei-integrität).

## Ontwikkeling en tests

```bash
pip install fritzconnection==1.15.1 segno==1.6.6 pytest
python3 -m pytest -q tests
node tests/test_card_editor_title.js custom_components/fritzbox_netzwerk/www/fritzbox-netzwerk-card.js
```

De repository bevat de tests voor 1.9.0 (`tests/test_issues_1_9_0.py`, `tests/conftest.py`, `tests/test_card_editor_title.js`); ze draaien tegen synthetische gegevens, niet tegen echte hardware. De tests van 1.8.0 voor `dns_settings.py` en `static_ip.py` zijn niet ingecheckt.

## Versiegeschiedenis

### 1.9.0 – Mesh-herkenning, gastwifi-service, bulkmarkering „gereserveerd”, repeater-aanmelding

Pakt de openstaande GitHub-issues aan voor zover dat zonder echte box kon. **Niets hiervan is getest op een echte FRITZ!Box of in een draaiende Home Assistant** – alleen tegen synthetische gegevens.

- **Nieuw (#27):** de lijst groeperen op **mesh-verbinding** (`group_by: mesh`).
- **Verbeterd (belasting):** minder verzoeken aan de FRITZ!Box. Zelden wijzigende gegevens (band per apparaat, mesh-topologie, extern IP, synchronisatiesnelheden) worden hoogstens elke 5 minuten opgehaald in plaats van bij elke update (circa 10–20 TR-064-aanroepen minder per cyclus, afhankelijk van de opstelling). Het kleinste ophaalinterval is nu 30 s (was 15 s); lagere opgeslagen waarden worden naar 30 s verhoogd. Het effect is berekend, niet gemeten op een box of in Home Assistant.
- **Verbeterd (kaart):** de lijst wordt hoogstens elke `refresh_interval` seconden opnieuw getekend (standaard 15, `0` = direct zoals voorheen), wacht tijdens scrollen of bedienen en behoudt de scrollpositie – de kaart springt niet meer naar boven. Kleine schommelingen van de verbindingssnelheid veroorzaken geen hertekening meer. Niet getest in een browser (alleen een Node-test van de rem).
- **Opgelost (#21):** de **wifi-band** ontbrak bij apparaten achter een repeater; die wordt nu ook uit de mesh-topologie gelezen (interfacenaam zoals `AP:5G:0` – aanname, niet getest). Een band uit de eigen wifi-lijst van de box heeft voorrang.
- **Opgelost (#16):** **niet alle mesh-repeaters werden herkend**: naast de modelnaam telt nu elk meshlid volgens de topologie (`is_meshed`) (niet getest).
- **Opgelost (#20):** de **QR-code van het gastwifi** toonde bij boxen met meer dan drie wifi-services een hoofdnetwerk. De gastservice wordt nu herkend (hoogste service vanaf 3 zonder bandmelding, anders 3 zoals voorheen); de gastschakelaar volgt dezelfde keuze; `gast_wlan_info` accepteert een optionele `service` en geeft `dienst` terug. De aanname „gast meldt geen band” is niet getest.
- **Opgelost (#25):** **repeater herstarten** mislukte bij repeaters met alleen een wachtwoord: na een geweigerde aanmelding wordt met een lege gebruikersnaam opnieuw geprobeerd.
- **Nieuw (#22, #23):** service `mark_devices_reserved` markeert veel apparaten via IP-patroon als „gereserveerd” (alleen Home Assistant). De box meldt reserveringen *binnen* het DHCP-bereik niet via TR-064, dus zulke apparaten verschijnen als „dynamisch” – een beperking van de interface, geen bug.
- **Niet opgelost (#24):** *offline apparaten verdwijnen* – geen oorzaak in de code gevonden; de diagnose-download bevat nu aantallen actief/inactief.
- **Niet geïmplementeerd (#26):** *dataverbruik per apparaat* – TR-064 levert geen verkeer per apparaat.
- **Al opgelost, issue nog open (#17):** de titel springt niet meer terug bij het wissen van het laatste teken (opgelost in 1.6.3); nieuwe test `tests/test_card_editor_title.js`.

### 1.8.0 – DNS-instellingen en statisch IP-adres (experimenteel)

- **Nieuw:** services `get_dns_settings` en `set_dns_settings` (optie „DNS-instellingen van de box wijzigen (experimenteel)”, voorvertoning met `dry_run`).
- **Nieuw:** service `set_static_ip` en een rij „Statisch IP” in het kaartvenster (optie „Statisch IP-adres instellen (experimenteel)”): vast IPv4-adres met controle op dubbele adressen en een herstartmelding. Categorieschakelaar `show_static_ip`.
- **Basis:** webinterface (REST `/api/v0/generic/…` voor DNS, `data.lua` voor statisch IP), geen TR-064. **Schrijven is op geen enkele echte box getest; de veldnamen voor het statische IP zijn aangenomen.**
- Vertalingen (de/en/nl) en tests tegen gesimuleerde boxen (47 gevallen).

Oudere versies: zie de Duitse [README.md](README.md#versionshistorie).

## Licentie

MIT
