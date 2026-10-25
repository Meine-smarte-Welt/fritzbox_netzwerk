**🌍 Sprache · Language · Taal · Langue · Idioma**

| 🇩🇪 [Deutsch](README.md) | 🇬🇧 [English](README.en.md) | 🇳🇱 **Nederlands** | 🇫🇷 [Français](README.fr.md) | 🇪🇸 [Español](README.es.md) |
|:---:|:---:|:---:|:---:|:---:|

# FRITZ!Box Netzwerk

Een Home Assistant-integratie die alle apparaten in het FRITZ!Box-thuisnetwerk als sorteerbare tabel op het dashboard zet – met IP-adres, MAC-adres, verbindingstype en de bijbehorende Home Assistant-apparaatnaam.

![Version](https://img.shields.io/badge/Version-2.0.1-blue)
![HACS](https://img.shields.io/badge/HACS-Custom-orange)

📺 **Video en handleiding voor de netwerkkaart (Duits):** [meinesmartewelt.de – FRITZ!Box Netzwerk voor Home Assistant](https://meinesmartewelt.de/fritzbox-netzwerk-home-assistant/)

> Dit is de Nederlandse uitgave. De Duitse [README.md](README.md) is het hoofdbestand en bevat de volledige kaartreferentie, het hoofdstuk probleemoplossing en de complete versiegeschiedenis. Onderdelen met „alleen Duits” zijn nog niet vertaald.

---

## Inhoud

- [Screenshots](#screenshots)
- [Functies](#functies)
- [Vereisten](#vereisten)
- [Installatie](#installatie)
- [Instellen](#instellen)
- [Instellingen](#instellingen)
- [Notification Center (optioneel)](#notification-center-optioneel)
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

## Screenshots

<p align="center"><img src="docs/images/banner.png" alt="FRITZ!Box Netzwerk" width="360"></p>

**Tab „Netwerk”** – alle apparaten als sorteerbare tabel met filterbalk (Actief, Inactief, Gast, Geblokkeerd, Update, Vast IP, VPN, Nieuw, Lang offline), IP- en MAC-adres, fabrikant, verbinding, koppeling naar het Home Assistant-apparaat, label en notitie.

![Tab Netwerk: apparatenlijst met filterbalk](docs/images/netzwerk.png)

**Tab „Online-monitor”** – actuele download- en uploadsnelheid met verloop, belasting per prioriteit en de grootste verbruikers. Tikken op een verbruiker opent de popup van het apparaat.

![Tab Online-monitor](docs/images/online-monitor.png)

**Detail-popup** – hier voor de FRITZ!Box: naam, IP- en MAC-adres, status, IP-type, internettoegang, filterprofiel, firmware-update, kenmerken en laatst online, plus de knoppen *Webinterface openen* en *Internet blokkeren*.

<img src="docs/images/geraete-popup.png" alt="Detail-popup van een apparaat" width="320">

**Tab „Instellingen”** – wifi-schakelaars, QR-code, MAC-filter, opnieuw verbinden, herstart, mesh-groep met online-teller en uitklapbare onderdelen (app-versie, FRITZ!Box met temperatuur, internetverbinding, thuisnetwerk).

![Tab Instellingen](docs/images/einstellungen.png)

Meer in de video en handleiding (Duits): [meinesmartewelt.de – FRITZ!Box Netzwerk voor Home Assistant](https://meinesmartewelt.de/fritzbox-netzwerk-home-assistant/).

---

## Functies

- Alle bekende netwerkapparaten van de FRITZ!Box als **één** tabel op het dashboard
- **Sorteerbaar** door op een kolomkop te klikken, ook met het toetsenbord; **zoeken** op naam, IP, MAC, model en Home Assistant-naam
- **Filterbalk**: Alle, Actief, Inactief, Gast, Geblokkeerd, Update, Vast IP, VPN – elke knop afzonderlijk te verbergen
- **Reserveringen van de box** (sinds 2.0.0, op geen enkele box getest): apparaten met „Dit netwerkapparaat altijd hetzelfde IPv4-adres geven” worden uit de webinterface gelezen en als vast geteld
- **VPN-apparaten** (sinds 2.0.0, ongetest): gesprekspartners die de box met VPN-markering maar zonder MAC-adres meldt, verdwijnen niet meer uit de lijst; de filterknop **VPN** (`filter_vpn: false` verbergt hem) toont alleen deze apparaten
- **README in vijf talen** (Duits, Engels, Nederlands, Frans, Spaans)
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

**Voorlopige versies (bèta, release candidate):** HACS toont ze alleen als je bij het downloaden **„Bètaversies tonen”** inschakelt. Met een geïnstalleerde bèta wijst de versieweergave in de kaart ook op nieuwere bèta's.

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
| Gast-wifi-service (sinds 1.9.1) | Automatisch | Nummer (1–4) van de wifi-service van de box die het gastnetwerk is. „Automatisch” herkent hem zelf; alleen wijzigen als gastschakelaar of QR-code het verkeerde netwerk tonen |
| Dagelijks op nieuwe versie controleren | aan | Vraagt eenmaal per dag bij GitHub naar de nieuwste versie; er worden geen gegevens over jou of de box verzonden |
| Toegangsprofielen van ouderlijk toezicht besturen (experimenteel) | uit | Schakelt de services en de profielkeuze in het detailvenster in |
| DNS-instellingen van de box wijzigen (experimenteel) | uit | Staat `set_dns_settings` toe te schrijven; lezen en voorvertoning werken altijd |
| Statisch IP-adres instellen (experimenteel) | uit | Staat `set_static_ip` en de kaartknop toe te schrijven; de voorvertoning (`dry_run`) werkt altijd |
| CPU en RAM van de box lezen (experimenteel) | uit | Drie sensoren uit de webinterface van de box |
| Netwerkapparaten als eigen apparaten aanmaken | uit | Eén HA-apparaat per geselecteerd apparaat, selectie via patroon |
| Meldingen naar het Notification Center sturen (sinds 2.0.0) | aan | Hoofdschakelaar voor de optionele koppeling, zie [Notification Center](#notification-center-optioneel) |
| Te verzenden soorten meldingen (sinds 2.0.0) | alle | Welke soorten meldingen naar het Notification Center gaan (verbinding verbroken, bewaakt apparaat offline, nieuw apparaat) |
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

De waarden – ook de **temperatuur** – verschijnen bovendien in de kaart op de tab *Instellingen* in het uitklapbare onderdeel *FRITZ!Box*. Staat de optie uit, dan staat daar een hint in plaats van de waarden.

---

## Dataverbruik per apparaat (experimenteel)

Optie “Dataverbruik per apparaat vastleggen (experimenteel)” (standaard uit). Ze beantwoordt **welk apparaat de afgelopen week hoeveel data heeft overgedragen**, om apparaten te vinden die te veel met internet praten of het wifi overbelasten (verzoek uit #26).

**Werking:** TR-064 levert geen verbruikscijfers per apparaat. De integratie leest daarom de **Online Monitor** van de box (webinterface, ongedocumenteerde REST-API `api/v0/monitor/…`), die per apparaat een **datasnelheid** levert, en telt die in de tijd op tot dag- en 7-dagentotalen (download en upload apart). De waarden zijn **schattingen**, geen tellerstanden van de box.

**Voorwaarden en grenzen:**
- In de FRITZ!Box moet per apparaat **“Internetdatasnelheden opslaan”** aan staan (Thuisnetwerk → Netwerk → apparaat → details; “Afzonderlijke apparaten” in de Online Monitor, FRITZ!OS 7.90/8.0 of nieuwer). Apparaten zonder deze instelling verschijnen niet.
- Tellen begint zodra de optie aan staat; de box levert geen waarden uit het verleden. Een volledige week duurt 7 dagen.
- De totalen staan in de opslag van Home Assistant (8 dagen). Als Home Assistant of het ophalen tijdelijk uitvalt, ontbreekt die tijd in de totalen (diagnose telt de gaten onder `traffic.stats`).
- **Eenheid alleen op plausibiliteit gecontroleerd:** byte per seconde; op een FRITZ!Box 5690 Pro (FRITZ!OS 8.40) past de ordegrootte bij de tellers van de box, een exacte vergelijking ontbreekt nog. Kloppen de cijfers niet, zet dan “Eenheid van de waarden van de online-monitor” op bit per seconde. De diagnose toont onder `traffic.shape.sample_values` ruwe voorbeeldwaarden om met de Online Monitor van de box te vergelijken.

**Sensoren:** De optie maakt *Dataverbruik status* (diagnose; toont „Gegevens beschikbaar”, „Wacht op metingen”, „Geen gegevensbron gekoppeld”, „Geen passende metingen” of „Fout bij ophalen”, de reden staat in de attributen), *Dataverbruik 7 dagen (alle apparaten)* en *Grootste dataverbruiker (7 dagen)* (apparaatnaam, top-vijf in de attributen). Elk apparaat met waarden krijgt ook *<apparaat> Daten 7 Tage* en *<apparaat> Daten heute* (eenheid byte, weergave in GB; download, upload en dagverloop als attributen). Apparaatsensoren verschijnen pas zodra er waarden zijn. **Zie je niets, kijk dan eerst naar de statussensor.**

**In de kaart:** kolom **Data (7 dagen)** met balk (klik op de kop om op de grootste verbruiker te sorteren); de popup toont “Data (7 dagen)” met download/upload, “Data vandaag” en een dagverloop. De kolom verschijnt alleen als er waarden zijn; verbergen met `show_traffic: false`. De CSV-export bevat de 7-dagenwaarde in byte.

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
- **Vangnet:** na het schrijven wordt de toestand opnieuw gelezen (`query.lua`, anders REST of `edit_device`). Is de toewijzing daarna niet actief, dan meldt de service een fout en herstelt – als ze eerder actief was – de vorige toestand. Alleen HTTP 200 geldt niet als succes. Kan de toestand niet worden teruggelezen, dan staat in het antwoord `geprueft: false` met een opmerking.
- **Tweefactorbevestiging:** vraagt de box om bevestiging, dan wordt niets gewijzigd. Een gebruiker met extra bevestiging kan ertoe leiden dat de box wijzigingen zonder melding negeert – gebruik voor de integratie een gebruiker zonder die bevestiging.

**Schrijfweg (sinds 2.0.0):** via de REST-interface van de webinterface, zoals een extern project die voor FRITZ!OS 8.25 beschrijft (`jvejmelka/fritzbox-static-lease`): `PUT /api/v0/generic/landevice/landevice/<UID>` met `{"static_dhcp": "1"}`; het gewenste adres komt als `"ip"` erbij. Tot 1.9.x gebruikte de integratie formuliervelden van `data.lua` die slechts *aangenomen* waren en die de box niet accepteerde – het wijzigen van het adres werkte niet. De oude weg is nu alleen nog een terugvaloptie als de box het REST-verzoek met een HTTP-fout beantwoordt (oudere FRITZ!OS).

**Teststatus (eerlijk):** de controle op dubbele adressen en de hele schrijfstroom zijn met tests tegen een **gesimuleerde** box gedekt. Op een **echte** FRITZ!Box **niet** getest: het veld `ip` van het REST-verzoek is zelfs in het externe project ongetest, de veldnamen van de terugvaloptie zijn aangenomen. Veel boxen blijven het oude adres melden tot het apparaat opnieuw verbindt – de service wijst daarop. Werkt het bij jou niet, open dan een issue met de foutmelding en de diagnose-download.

---

## Notification Center (optioneel)

De integratie kan meldingen naar het **Notification Center** sturen – een aparte, eveneens
optionele „Meine smarte Welt”-integratie die meldingen verzamelt, op urgentie sorteert en aflevert. **Zonder geïnstalleerd
Notification Center gebeurt er niets:** geen fout, geen extra logregel, geen extra aanvraag bij de FRITZ!Box.

De integratie meldt via de Home Assistant-gebeurtenisbus (geen MQTT, geen broker). De teksten stuurt zij eenmalig bij het
aanmelden in vijf talen (de, en, nl, fr, es); het Notification Center kiest de weergavetaal. Bij het opstarten meldt zij
alleen de **beginsituatie** (zichtbaar, zonder push), daarna alleen statuswijzigingen – geen herhalingen.

| Soort melding | Urgentie | Treedt op als … | Sluit zich |
| --- | --- | --- | --- |
| Verbinding met FRITZ!Box verbroken | Waarschuwing | een aanvraag bij de box mislukt (dan worden ook de entiteiten „niet beschikbaar”) | bij de volgende geslaagde aanvraag |
| Bewaakt apparaat offline | Info | een bewaakt apparaat in de apparatenlijst niet meer actief is | zodra het weer actief is |
| Nieuw apparaat in het netwerk | Info | een apparaat voor het eerst in het thuisnetwerk verschijnt (dezelfde trigger als de gebeurtenisentiteit „Nieuw apparaat”) | eenmalige melding, blijft tot bevestiging in het Notification Center |

**Bewaakt** zijn precies de apparaten waarvoor de integratie al een „Verbonden”-status aanmaakt: repeaters (instelling
„Repeaters als eigen apparaten aanmaken”) en de via IP-patroon gekozen netwerkapparaten (instelling „Netwerkapparaten als
eigen apparaten aanmaken”). Alle andere apparaten melden alleen „Nieuw apparaat”.

**Instellen** onder *Configureren*: een hoofdschakelaar „Meldingen naar het Notification Center sturen” en een keuze
„Te verzenden soorten meldingen” (op urgentie gesorteerd). Uit betekent: er wordt niets verzonden en het Notification
Center sluit al open meldingen van die soort. Een wijziging laadt de integratie opnieuw, net als elke andere instelling.
De schakelaars bestaan **alleen in dit dialoogvenster**, niet in de dashboardkaart.

**Wat in de meldingen staat:** de apparaatnaam (bij „Nieuw apparaat” ook het IP-adres), verder niets – geen
inloggegevens, geen fabrikant- of verbindingsgegevens. Het MAC-adres dient als technische identificatie zodat een melding
later weer gesloten kan worden; het staat in de gebeurtenis, niet in de meldingstekst. Noch namen noch adressen komen in
het logboek of de diagnose-download; de download toont alleen de schakelaarstand en hoeveel meldingen per soort sinds de
start zijn verzonden.

**Grenzen:**

- Er is bewust **geen eigen vertraging** en geen nieuwe drempel: meldt de box een bewaakt apparaat in één aanvraag als
  inactief, dan ontstaat de melding en sluit zij bij de volgende aanvraag waarin het weer actief is. Vind je dat te
  onrustig, schakel dan de soort „Bewaakt apparaat offline” uit.
- „Nieuw apparaat” meldt een apparaat dat verscheen terwijl Home Assistant uit was na het opstarten als beginsituatie
  (zichtbaar, zonder push). Direct na het instellen meldt het – zoals de gebeurtenisentiteit – niets.
- Mislukt het inloggen herhaaldelijk en vraagt Home Assistant daarom om opnieuw in te loggen, dan is dat geen melding
  „verbinding verbroken”; daarvoor toont Home Assistant zelf een melding.
- **Teststatus:** alleen getest tegen een **gesimuleerde** gebeurtenisbus (koppeling en triggers, 44 tests). **Niet** tegen
  een echt Notification Center en niet op een echte FRITZ!Box of in een draaiende Home Assistant. Feedback
  uitdrukkelijk gewenst.

---

## De dashboardkaart

De kaart wordt met de integratie meegeleverd (`custom:fritzbox-netzwerk-card`). Hij heeft een grafische editor; elke kolom, elk filter, de besturingsbalk en de rijen van het detailvenster zijn afzonderlijk aan of uit te zetten, kleuren zijn vrij te kiezen, drie talen. De volledige referentie (kolommen, sorteren, IP-filter, tabs, groeperen, CSV-export, gast-wifi-QR-code, vegen op telefoons, kleuren) staat in de Duitse README.

**Tabs (optioneel):** met *Categorieën als tabs tonen* krijgt de kaart een tabbalk. **Netwerk** bevat de apparatentabel. **Online-monitor** toont de actuele snelheid, belasting per prioriteit, verbindingsdetails en online-tellers; tik op een grootste verbruiker om de popup van dat apparaat te openen. **Mesh** tekent de FRITZ!Box, repeaters en hun apparaten: tik op de box of een repeater om de popup te openen, tik op „N apparaten” om de apparatenlijst van het knooppunt uit te klappen en tik op een apparaat daarin voor de popup. **Instellingen** (altijd de laatste tab) bevat de schakelaars en de uitklapbare onderdelen *App-versie*, *FRITZ!Box* (model, FRITZ!OS, IP-adres, looptijd, plus temperatuur, CPU en RAM met de optie „CPU en RAM van de box lezen”), *Internetverbinding* en *Thuisnetwerk*. Video en handleiding (Duits): [meinesmartewelt.de](https://meinesmartewelt.de/fritzbox-netzwerk-home-assistant/).

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
default_filter: aktiv   # alle | aktiv | inaktiv | gast | gesperrt | update | fest | vpn
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
| `gast_wlan_info` | Gast-wifigegevens (voor de QR-code); sinds 1.9.0 wordt de gastservice herkend en kan een optionele `service` (1-4) die afdwingen; sinds 1.9.1 geeft de kaart het bekende nummer door en kan de instelling „Gast-wifi-service” het vastleggen |
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

Duits, Engels en Nederlands – in de config flow, entiteiten, services en de kaart (taal uit Home Assistant, terugval Engels). De **README** is beschikbaar in vijf talen: Duits, Engels, Nederlands, Frans en Spaans (taalbalk bovenaan elk bestand).

## Beveiliging

Schrijfacties vereisen beheerdersrechten; invoer wordt in de backend gecontroleerd; teksten in de kaart worden geëscaped. Opties voor experimentele schrijffuncties staan **standaard uit** en riskante acties hebben waar mogelijk een voorvertoning (`dry_run`).

---

## Bekende beperkingen

- **Notification Center (sinds 2.0.0)** is alleen getest tegen een gesimuleerde gebeurtenisbus, niet tegen een echt Notification Center of echte hardware; de schakelaars bestaan alleen in het dialoogvenster Configureren, niet in de kaart, zie [Notification Center](#notification-center-optioneel).
- **„Alle ongebruikte verbindingen verwijderen” ontbreekt** – TR-064 heeft daarvoor geen actie.
- **Statisch IP en DNS schrijven zijn experimenteel** en gebruiken de ongedocumenteerde webinterface van de box. Schrijven is op geen enkele echte box getest; de REST-route voor het statische IP volgt de beschrijving van een extern project voor FRITZ!OS 8.25. Ze kunnen met elke FRITZ!OS-update breken.
- **DHCP-reserveringen maar deels herkend.** De box meldt reserveringen *binnen* het DHCP-bereik niet via TR-064. Sinds 2.0.0 leest de integratie ze extra uit de webinterface (`query.lua`, anders `netDev`); of jouw FRITZ!OS de markering levert, is ongetest. Zo niet, dan blijven zulke apparaten „dynamisch” – de diagnose-download (`reservations`) toont welke weg werkte. Alternatief: handmatig of in bulk markeren (`mark_devices_reserved`).
- **Mesh maar gedeeltelijk:** geen signaalsterkte in dBm.
- **Dataverbruik per apparaat** levert de box niet via TR-064.
- **VPN-apparaten (issue #29):** vermeldingen zonder MAC-adres werden eerder als verlopen weggegooid; gesprekspartners die de box als VPN markeert (markering `X_AVM-DE_VPN` of interfacetype VPN/WireGuard/IPsec) en een IP-adres hebben, blijven sinds 2.0.0 behouden, met de id `VPN:<IP>`. Ze verschijnen in lijst en tellers maar krijgen geen entiteiten en geen acties die een MAC-adres vereisen (wekken, blokkeren, hernoemen, statisch IP). **Of de box WireGuard-gesprekspartners zo meldt, is ongetest**; een gedocumenteerde interface om ze apart op te vragen ken ik niet. De diagnose-download (`box_hosts.without_mac_samples`) toont hoe de box zulke vermeldingen markeert.
- Apparaten worden uitsluitend via het MAC-adres aan Home Assistant-apparaten gekoppeld.
- De volledige lijst staat in de Duitse README.

## Probleemoplossing

Alleen Duits: zie het hoofdstuk „Fehlerbehebung” in [README.md](README.md#fehlerbehebung). Twee opmerkingen: HACS bepaalt zelf wanneer een nieuwe release verschijnt (issue #28) – gebruik ⋮ → *Informatie bijwerken* bij de repository in HACS; en voor ontbrekende offline-apparaten (issue #24) eerst de instelling „Verbroken apparaten verbergen” en het standaardfilter van de kaart controleren – tot 2.0.0 maakte die instelling ook de weergaven „Inactief” en „Lang offline” leeg. Ontbreken er nog apparaten, voeg dan de diagnose-download en het debuglog aan het issue toe – daarin staat hoeveel items de box leverde (`box_hosts`). Logger: `custom_components.fritzbox_netzwerk`; de diagnose-download is geanonimiseerd.

## Bestandsintegriteit

Elk `.py`-, `.js`- en `.yaml`-bestand begint met een SHA-256-header over de inhoud (vanaf regel 2). Controleren met `tail -n +2 bestand.py | sha256sum`. De hashes van de JSON-bestanden staan in de Duitse [README.md](README.md#datei-integrität).

## Ontwikkeling en tests

```bash
pip install fritzconnection==1.15.1 segno==1.6.6 pytest
python3 -m pytest -q tests
node tests/test_card_editor_title.js custom_components/fritzbox_netzwerk/www/fritzbox-netzwerk-card.js
```

De tests voor 2.0.0 (`test_issue30_dns.py`, `test_static_ip.py`, `test_vpn_and_reservations.py`, met een eigen `conftest.py` die de modules zonder Home Assistant laadt) worden eveneens als apart pakket geleverd, niet in de repository. Ze draaien tegen een gesimuleerde FRITZ!Box.

De tests voor het Notification Center in 2.0.0 (`test_notification_bridge.py`, `test_nc_catalog.py`, `test_coordinator_nc.py`, `test_updates_prerelease.py`, met een eigen `conftest.py` die Home Assistant door attrappen vervangt) worden als apart pakket bij de release geleverd, niet in de repository.

De repository bevat de tests voor 1.9.0 (`tests/test_issues_1_9_0.py`, `tests/conftest.py`, `tests/test_card_editor_title.js`); ze draaien tegen synthetische gegevens, niet tegen echte hardware. De tests van 1.8.0 voor `dns_settings.py` en `static_ip.py` zijn niet ingecheckt.

## Versiegeschiedenis

### 2.0.1 – Toegangsprofielen met echte namen, Meshkaart met cascade en wolken, naam van de FRITZ!Box

Verbeteringen en oplossingen ten opzichte van 2.0.0 na reacties. **Getest:** de profielnamen en de profielenlijst, alleen lezend op een echte FRITZ!Box 5690 Pro (FRITZ!OS 8.40). **Niet getest op een echte FRITZ!Box of in een draaiende Home Assistant:** al het overige – de meshverwerking draaide alleen tegen nagebouwde topologieën (met de echte klassen van `fritzconnection`) en de kaart tegen testgegevens in een gesimuleerde browser.

**Kaart**

- **Opgelost – profielnamen in de keuzelijst (reactie):** De keuze van de toegangsprofielen toonde `filtprof1`, `filtprof2` … in plaats van namen. Nu staan daar de namen van de box („Standard", „Gast", „Unbeschränkt", plus je eigen profielen). Hebben twee profielen dezelfde naam, dan staat de ID tussen haakjes erachter.
- **Nieuw – boomweergave (tabblad „Mesh"):** Repeaters achter een repeater (cascade) worden als boom getekend; bij elke verbinding staat de datasnelheid.
- **Opgelost – repeater achter repeater (reactie):** Alle repeaters leken rechtstreeks aan de FRITZ!Box te hangen. Kan de uplink van een repeater aan geen enkel lid worden gekoppeld, dan hangt de kaart hem onder de naam van zijn uplink en pas daarna onder de box.
- **Nieuw – wolken per station:** Onder de FRITZ!Box en onder elke repeater hangen wolken met de verbonden apparaten, gesplitst in **WLAN** en **LAN** (plus „Overig" als de soort niet te herkennen is). Apparaten achter een **switch** staan in de LAN-wolk van het station waar de switch aan hangt – de FRITZ!Box meldt switches niet afzonderlijk.
- **Nieuw – totaalaantal bij de FRITZ!Box:** De box toont „N apparaten totaal"; in het uitklapbare gedeelte staat „10 direct · 15 totaal". Repeaters in de lijst van hun station verschijnen met „↳".
- **Opgelost – naam in plaats van model:** De FRITZ!Box verscheen met zijn modelnaam („FRITZ!Box 5530 Fiber"). Nu staat zijn naam uit het thuisnetwerk (vermelding van de box in de apparatenlijst, anders de naam uit de mesh-topologie); het model staat eronder.
- **Opgelost – box niet met zichzelf verbonden:** De eigen vermelding van de FRITZ!Box verschijnt niet meer in de apparatenlijst van zijn eigen station.
- **Verbeterd – snelheden:** Ontbreekt de actuele datasnelheid (vaak bij kabelverbindingen en sommige repeaters), dan geldt de maximale snelheid van de verbinding. De waarde is ongetest; zonder beide waarden blijft „—" staan.
- De kolom en het pop-up „Verbonden via" tonen de naam van het station uit de mesh.

**Integratie**

- **Opgelost – profielnamen en profielenlijst (FRITZ!OS 8.40):** Namen werden alleen uit een attribuut `data-name` gelezen, dat de box niet levert. Bovendien antwoordt FRITZ!OS 8.40 op de pagina `kidPro` alleen nog met het overzicht – de profielenlijst was daar helemaal niet te lezen. Nu worden de namen gelezen uit de apparaatkeuze van de box (`edit_device`), uit het pad `api/v0/generic/filter_profile` (waar de standaardprofielen een lege naam hebben), uit `kidPro` en uit `kidLis`; voor de drie vaste profielen gelden als laatste terugval „Standard" (`filtprof1`), „Gast" (`filtprof2`) en „Unbeschränkt" (`filtprof3`). Alleen lezend bevestigd op een FRITZ!Box 5690 Pro (FRITZ!OS 8.40).
- **Nieuw – diagnose bij ontbrekende namen:** Wordt nergens een naam gevonden, dan toont de keuze de ID en komt er per start één waarschuwing in het logboek („Zugangsprofile ohne Namen") met een kort fragment van de pagina `kidPro` (zonder sessie-ID).
- **Opgelost – gecascadeerde repeaters:** De meshverwerking sloeg tot nu toe alle apparaten met meerdere actieve verbindingen over – juist de repeaters met eigen apparaten. Nu wordt de uplink van elk apparaat bepaald via de gunstigste weg naar de hoofdbox: verbindingen met een gemelde actuele datasnelheid tellen zwaarder dan die zonder, en clients (smartphones, pc's …) geven nooit door. Een extra, als verbonden gemarkeerde verbinding tussen repeater en hoofdbox (bijvoorbeeld een verouderd item zonder actuele snelheid) wint dus niet meer van de echte weg via een andere repeater. Of de box zulke items echt meldt, is ongetest. Ook repeaters krijgen „Verbonden via" en een datasnelheid. Nieuwe attributen per apparaat: `via_id`, `link_type`, `mesh_id`; de mesh-leden dragen `mesh_id`, `via_id`, `connected_via`, `link_mbit`, `link_type`.
- **Nieuw – naam als terugval voor repeaters:** Past het MAC-adres van een repeater in de apparatenlijst bij geen enkele interface van de mesh-topologie, dan wordt hij via zijn unieke naam gekoppeld. Bij dubbelzinnige namen wordt niets geraden.
- **Nieuw – diagnose-export:** Twee nieuwe onderdelen, `mesh_topology` (geanonimiseerd: knooppunten met rol, model, afstand en uplink, verbindingen met soort, status en snelheid) en `mesh_resolution` (hoe de kaart elke repeater indeelt). De mesh-ID's `mesh_id` en `via_id` (afgeleid van het MAC-adres van het apparaat) worden in het export nu afgeschermd.
- **Opgelost – timeout bij `get_access_profile` (reactie over de 5530):** `Read timed out (read timeout=10)`. Het apparaat wordt nu eerst in de lichte apparatenlijst gezocht (dezelfde route als het vaste IP-adres); de zware pagina's van de webinterface (`netDev`, `edit_device`, `kidPro`) mogen tot 40 seconden antwoorden. Of de timeout op de 5530 daarmee verdwijnt, is ongetest.

**Updatetips:** Bijwerken via HACS, Home Assistant herstarten, browsercache legen (Ctrl+F5).

**Bekend:** In zijn eigen apparaatkeuze biedt de FRITZ!Box het profiel „Gast" niet aan (op één apparaat waargenomen); de integratie toont het toch. Of de box de toewijzing accepteert, is ongetest – anders verschijnt de melding dat het profiel niet is overgenomen. Hoe de box apparaten achter een switch meldt, hangt van FRITZ!OS af; de toewijzing aan een station is ongetest. Blijft de meshweergave plat, stuur dan de diagnose-download van de invoer (menu ⋮ → „Diagnose downloaden") met de onderdelen `mesh_topology` en `mesh_resolution` mee; daarin staan geen namen of adressen.

### 2.0.0 – Online-monitor en Mesh-kaart, FRITZ!Box-info met temperatuur, Notification Center, dataverbruik per apparaat, statisch IP via REST

Eerste stabiele versie van de 2.0-reeks. Bouwt voort op 1.9.1 en bevat alles uit de voorafgaande voorlopige versies (bèta's), die niet meer worden aangeboden. **Niet getest op een echte FRITZ!Box of in een draaiende Home Assistant** – alleen tegen een gesimuleerde box, synthetische gegevens en de kaart in een headless browser. De formaten van *verbindingsdetails* en *online-monitor* zijn in de browser gelezen op een FRITZ!Box 5690 Pro (FRITZ!OS 8.40), alleen lezen; de opbouw van de *online-tellers* is onbekend en wordt tolerant gelezen.

**Kaart**

- **Nieuw – Online-monitor:** de **grootste verbruikers** zijn aan te tikken en openen de popup van het apparaat.
- **Nieuw – Mesh:** tikken op de FRITZ!Box of een repeater opent de popup. „N apparaten” klapt de apparatenlijst van het knooppunt uit en elk apparaat daarin opent zijn popup. Lange lijsten scrollen binnen het onderdeel, zodat het overzichtelijk blijft.
- **Nieuw – Instellingen:** uitklapbare onderdelen **FRITZ!Box** (model, FRITZ!OS, IP-adres, looptijd, **temperatuur**, CPU- en RAM-belasting), **Internetverbinding** (status, extern IP, online-duur, snelheden, maximaal tempo) en **Thuisnetwerk** (aantallen apparaten, mesh-stand). Temperatuur, CPU en RAM verschijnen alleen met de optie „CPU en RAM van de box lezen (experimenteel)”; anders staat er een hint. De looptijd wordt via TR-064 (`DeviceInfo`) gelezen; niet getest op een echte box.
- **Nieuw – tab „Online-monitor”** (`mdi:chart-areaspline`): actuele down-/uploadsnelheid met verloop, belasting per prioriteit, grootste verbruikers, **verbindingsdetails** (gebruikersnaam en wachtwoord worden nooit overgenomen) en **online-tellers**. Verschijnt alleen met ingeschakelde dataverbruikregistratie.
- **Nieuw – tab „Mesh”** (`mdi:router-network`): kaart zoals *Thuisnetwerk → Mesh* van de box met FRITZ!Box, repeaters en de verbonden apparaten inclusief verbindingssnelheid. Verschijnt alleen met minstens één repeater.
- **Gewijzigd:** de tab „Besturing” heet nu **„Instellingen”** (tandwiel, altijd de laatste tab); de app-versie staat daar als uitklapbaar onderdeel.
- **Nieuw:** filterknop **VPN** (apparaten die de box als VPN markeert en items die als `VPN:<IP>` worden bewaard; verbergen met `filter_vpn: false`, pictogramkleur `color_cat_vpn`).
- **Nieuw:** kolom „Data (7 dagen)”, popuprijen met dagverloop, CSV-export in bytes (`show_traffic`).

**Integratie**

- **Nieuw – dataverbruik per apparaat (experimenteel, #26 gedeeltelijk):** opties „Dataverbruik per apparaat registreren” en „Eenheid van de meetwaarden van de online-monitor”. De integratie leest de datasnelheden per apparaat uit de online-monitor (`api/v0/monitor/online/0`, andere paden als terugval), rekent ze om naar dag- en 7-dagentotalen en bewaart ze blijvend. Sensoren: *Dataverbruik status* (noemt de reden als waarden ontbreken), *Dataverbruik 7 dagen (alle apparaten)*, *Grootste dataverbruiker (7 dagen)* en per apparaat *Data 7 dagen* en *Data vandaag*. Waarden zijn schattingen; eenheid, vensterlengte en toewijzing zijn niet getest. Diagnose: `traffic`, `traffic.online_extras`.
- **Nieuw – Notification Center (optioneel):** meldingen *Verbinding met FRITZ!Box verbroken*, *Bewaakt apparaat offline* en *Nieuw apparaat op het netwerk* via de gebeurtenisbus, teksten in vijf talen, twee schakelaars onder *Configureren*. Zonder Notification Center verandert er niets. Zie [Notification Center](#notification-center-optioneel).
- **Verbeterd:** bij een geïnstalleerde bèta of release candidate houdt de updatecontrole ook rekening met voorlopige versies; met een definitieve versie zie je nog steeds alleen definitieve versies.
- **Nieuw – documentatie:** de README is er in vijf talen (de, en, nl, fr, es) met taalbalk en screenshots.

**Opgelost**

- **Mesh-kaart:** repeaters verschenen in de apparatenlijst van hun knooppunt als gewone apparaten, omdat de kaart de vlag `repeater` van de integratie niet kende. Repeaters tellen nu alleen als knooppunt.
- **IP-adres wijzigen:** `set_static_ip` en de rij „Statisch IP” in de kaart werkten niet, omdat de formuliervelden van `data.lua` alleen aangenomen waren. De integratie schrijft nu via de REST-route die een externe project voor FRITZ!OS 8.25 beschrijft (`PUT /api/v0/generic/landevice/landevice/<UID>`), leest het resultaat terug, meldt een genegeerde wijziging als fout en herstelt de eerdere toewijzing. Het veld `ip` van het verzoek is zelfs in dat externe project niet getest.
- **#30:** `set_dns_settings` draaide op een FRITZ!Box 6591 Cable de IPv4-waarde terug, omdat een IPv6-adres als tekenreeks werd vergeleken (de box verkort `:0:` tot `::`). IP-adressen worden nu als adressen vergeleken.
- **#31:** apparaten met „altijd hetzelfde IPv4-adres toewijzen” binnen het DHCP-bereik ontbraken in het filter „Vast IP”. De integratie leest de reserveringen nu ook uit de webinterface; of jouw FRITZ!OS de vlag levert, is niet getest (diagnose: `reservations`).
- **#29 (waarschijnlijke oorzaak):** items zonder MAC-adres (bijv. WireGuard-peers) werden weggegooid. Als VPN gemarkeerde peers met een IP-adres blijven nu bewaard als `VPN:<IP>`.
- **#24 (één mogelijke oorzaak):** „Verbroken apparaten verbergen” maakte ook de weergaven „Inactief” en „Lang offline” leeg. De instelling geldt nu alleen nog voor de gemengde weergaven.

**Update-instructies:** bijwerken via HACS, Home Assistant herstarten, browsercache legen (Ctrl+F5).

**Bekend:** of de online-tellers op jouw box worden herkend, blijkt pas bij testen; zo niet, dan helpt de diagnose-download. #26 (datavolume per apparaat) blijft een schatting, TR-064 levert het niet.

### 1.9.1 – Kiesbare gast-wifi-service, IPv6-DNS met HTTP 400, uitgebreide diagnose

Bouwt voort op 1.9.0. **Niets hiervan is getest op een echte FRITZ!Box of in een draaiende Home Assistant** – alleen tegen synthetische gegevens.

- **Nieuw (#20):** instelling **„Gast-wifi-service”** (automatisch, 1–4). De kaart geeft het bekende servicenummer door aan `gast_wlan_info` (attribuut `controls.guest_service`); gastschakelaar en QR-code volgen hetzelfde nummer. De diagnose-download toont `wlan_service_bands`. Het voorstel uit het issue (vast service 4) is niet overgenomen, omdat het gastnetwerk op andere boxen service 3 is.
- **Opgelost (#30):** `set_dns_settings` draaide op een FRITZ!Box 6591 Cable de IPv4-waarde terug, omdat het schrijven van `home_ipv6_dns` met HTTP 400 antwoordt terwijl de box de waarde overneemt. Een HTTP-fout bij het schrijven van IPv6 geldt nu als geschreven als opnieuw lezen de gewenste waarde toont (met een `hinweis` in het antwoord); anders verandert er niets. Ongetest op een box.
- **Opgelost (#17):** de **kaarttitel** sprong in de editor terug naar „Netzwerkgeräte” bij het wissen van het laatste teken. Oorzaak: huidige Home Assistant meldt een leeggemaakt tekstveld als `undefined` in plaats van een lege tekst, wat niet als „bewust leeggemaakt” werd herkend. Een **lege titel is nu toegestaan**: hij blijft leeg, wordt als lege tekst opgeslagen en de kaart toont dan geen kop. Een nieuwe kaart zonder titel toont nog steeds „Netzwerkgeräte”. In de browser getest met nagebootst gedrag van Home Assistant, niet in een echt dashboard.
- **Verbeterd (#24):** diagnose-download en debuglog tonen hoeveel apparaten de box leverde (`box_hosts`: `raw_total`, `raw_active`, `raw_without_mac`). **De oorzaak van verdwijnende offline-apparaten is niet gevonden en niet opgelost.**
- **Documentatie:** probleemoplossing voor #28 (HACS toont updates pas na „Informatie bijwerken”) en #24; opmerking over VPN-apparaten (#29) onder bekende beperkingen.
- **Niet uitgevoerd:** #29 (VPN-gesprekspartners in de apparatenlijst) – zonder box of voorbeeldgegevens niet te controleren; #26 (dataverbruik per apparaat) – niet beschikbaar via TR-064; #28 ligt aan HACS, niet aan de integratie.

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
