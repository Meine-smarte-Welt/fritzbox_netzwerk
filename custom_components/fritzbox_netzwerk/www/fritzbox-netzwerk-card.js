/**
 * FRITZ!Box Netzwerk - Dashboard-Karte
 * Teil der Integration fritzbox_netzwerk (Meine-smarte-Welt).
 *
 * Bewusste Entwurfsentscheidungen:
 *
 * - Light DOM statt Shadow DOM. Im Shadow DOM loest <ha-icon> seine
 *   Icon-Definitionen unzuverlaessig auf, und ein zweiter Ladeweg der
 *   Moduldatei bricht dort still mit einer DOMException ab. Alle
 *   CSS-Klassen tragen deshalb das Praefix "fbn-", damit nichts in
 *   fremde Karten ausblutet.
 * - Skelett-Rendering: Werkzeugleiste und Tabellenkopf werden genau
 *   einmal gebaut, bei neuen Daten wird nur der <tbody> ersetzt. Damit
 *   verliert das Suchfeld bei jeder Aktualisierung des Sensors weder
 *   Fokus noch Inhalt und die Scrollposition bleibt stehen.
 * - Ein customElements.get()-Waechter verhindert, dass ein doppelt
 *   eingebundenes Modul beim zweiten define() abbricht.
 */

const FBN_VERSION = "1.7.0";

/* ------------------------------------------------------------------ */
/* Konfiguration                                                       */
/* ------------------------------------------------------------------ */

const CONFIG_DEFAULTS = {
  entity: "",
  title: "Netzwerkgeräte",
  show_title: true,
  language: "",

  // Spalten
  show_status: true,
  show_name: true,
  show_ip: true,
  show_mac: true,
  show_connection: true,
  show_ha_name: true,
  show_ip_type: true,
  show_wan: true,
  show_update: true,
  show_speed: true,
  show_model: false,
  show_type: false,
  show_last_seen: false,
  // Hersteller zur MAC-Adresse (aus der mitgelieferten OUI-Tabelle).
  show_vendor: false,
  // Funkband (2,4 / 5 / 6 GHz), in dem ein WLAN-Gerät gerade verbunden ist.
  show_band: false,
  // Mesh-Nachbar (FRITZ!Box oder Repeater), über den ein Gerät gerade
  // verbunden ist (Idee 5 aus feature-ideen.md). Nur bei mindestens einem
  // Repeater im Heimnetz überhaupt gefüllt.
  show_connected_via: false,
  // Eigenes Etikett und eigene Notiz je Gerät (Idee 3) - nur in Home
  // Assistant gespeichert, bearbeitbar im Detail-Popup.
  show_label: false,
  show_note: false,
  // Gruppierung der Liste (Idee 18): "", "state", "connection", "vendor",
  // "band", "subnet" oder "label".
  group_by: "",
  show_group_select: true,
  // CSV-Export der sichtbaren Liste (Idee 18).
  show_csv_export: true,
  // Filter, Sortierung, Gruppierung und eingeklappte Gruppen pro Browser
  // merken (localStorage; Idee 18).
  remember_view: true,

  // Darstellung
  show_summary: true,
  show_search: true,
  show_filter: true,
  show_controls: false,
  // Versionsanzeige samt Update-Hinweis auf der Steuerungsseite (nur sichtbar, wenn die
  // Steuerungsleiste an ist).
  show_version: true,
  // Zugangsprofil (Kindersicherung) im Detail-Popup - erscheint nur, wenn die Funktion in
  // den Integrationsoptionen eingeschaltet ist.
  show_parental: true,
  show_tabs: false,
  // Einzelne Filter-Buttons an/aus (nur wirksam, wenn show_filter an ist).
  filter_alle: true,
  filter_aktiv: true,
  filter_inaktiv: true,
  filter_gast: true,
  filter_gesperrt: true,
  filter_update: true,
  // Nur Geräte mit fester oder reservierter IP-Adresse (aktiv und inaktiv).
  filter_fest: true,
  // Nur Geräte, die innerhalb der letzten 7 Tage zum ersten Mal gesehen
  // wurden (siehe hosts.apply_first_seen()/coordinator._update_first_seen()).
  filter_neu: true,
  // Nur inaktive Geräte, die seit mindestens 30 Tagen nicht mehr gesehen
  // wurden (oder noch nie, seit last_seen erfasst wird) - Arbeitsgrundlage
  // zum Aufräumen alter Einträge.
  filter_lange_offline: true,
  // Welcher Filter beim Laden/Neuöffnen aktiv ist. Standardmäßig
  // "aktiv" (vorher "alle"); über den Editor oder default_filter änderbar.
  default_filter: "aktiv",
  hide_inactive: false,
  // IP-Filter mit Platzhaltern: zeigt nur Geräte, deren IP-Adresse passt.
  // Mehrere Muster mit Komma, Semikolon oder Leerzeichen trennen; "*" steht
  // für beliebig viele, "?" für genau ein Zeichen, "!" vor einem Muster
  // schließt Treffer aus. Leer = alle Geräte. Beispiel: "192.168.2.*".
  ip_filter: "",
  // Klick auf die MAC-Adresse in der Tabelle kopiert sie (statt das Popup zu
  // öffnen). Im Popup bleibt der Kopier-Knopf in jedem Fall.
  mac_click_copies: true,
  compact: false,
  max_rows: 0,
  // Höchstzahl gleichzeitig sichtbarer Zeilen; darüber wird der
  // Datenbereich scrollbar, Kopf und Auswahl bleiben stehen. 0 = alle.
  max_visible_rows: 0,
  show_details_popup: true,
  open_device_on_click: true,
  show_scroll_arrows: true,
  sticky_name: true,
  ip_opens_web: true,
  ip_web_fallback: true,

  // Sortierung
  sort_by: "ip",
  sort_dir: "asc",

  // Farben (leer = Wert des aktiven Themes)
  color_header_bg: "",
  color_header_text: "",
  color_row_text: "",
  color_row_alt_bg: "",
  color_border: "",
  color_active: "",
  color_inactive: "",
  color_guest: "",
  color_blocked: "",
  color_update: "",
  color_static: "",
  color_accent: "",
  // Symbolfarbe je Kategorie-Chip (leer = folgt dem Akzent/Theme).
  color_cat_alle: "",
  color_cat_aktiv: "",
  color_cat_inaktiv: "",
  color_cat_gast: "",
  color_cat_gesperrt: "",
  color_cat_update: "",
  color_cat_fest: "",
  color_cat_neu: "",
  color_cat_lange_offline: "",
};

/**
 * Spaltendefinition. "prio" steuert das Verhalten auf schmalen Karten:
 * 3 verschwindet zuerst, dann 2. Spalten mit prio 1 bleiben immer.
 */
const COLUMNS = [
  { key: "status", cfg: "show_status", label: "", short: "", prio: 1, sortable: true, align: "center" },
  { key: "name", cfg: "show_name", label: "Gerät", prio: 1, sortable: true },
  { key: "ip", cfg: "show_ip", label: "IP-Adresse", prio: 1, sortable: true },
  { key: "mac", cfg: "show_mac", label: "MAC-Adresse", prio: 3, sortable: true },
  { key: "vendor", cfg: "show_vendor", label: "Hersteller", prio: 3, sortable: true },
  { key: "connection", cfg: "show_connection", label: "Verbindung", prio: 2, sortable: true },
  { key: "band", cfg: "show_band", label: "Funkband", prio: 3, sortable: true },
  { key: "connected_via", cfg: "show_connected_via", label: "Verbunden über", prio: 3, sortable: true },
  { key: "ha_name", cfg: "show_ha_name", label: "Home Assistant", prio: 2, sortable: true },
  { key: "label", cfg: "show_label", label: "Etikett", prio: 2, sortable: true },
  { key: "note", cfg: "show_note", label: "Notiz", prio: 3, sortable: true },
  { key: "ip_type", cfg: "show_ip_type", label: "IP-Typ", prio: 3, sortable: true },
  { key: "wan", cfg: "show_wan", label: "Internet", prio: 3, sortable: true, align: "center" },
  { key: "update", cfg: "show_update", label: "Update", prio: 3, sortable: true, align: "center" },
  { key: "speed", cfg: "show_speed", label: "Tempo", prio: 3, sortable: true, align: "right" },
  { key: "model", cfg: "show_model", label: "Modell", prio: 3, sortable: true },
  { key: "type", cfg: "show_type", label: "Gerätetyp", prio: 3, sortable: true },
  { key: "last_seen", cfg: "show_last_seen", label: "Zuletzt online", prio: 3, sortable: true },
];

// Entspricht NEW_DEVICE_FILTER_DAYS in const.py - duplizieren statt teilen,
// da die Karte unabhängig von den Python-Dateien geladen wird.
const NEW_DEVICE_FILTER_DAYS = 7;

// Schwelle fuer den Filter "Lange offline" (Idee 6 aus feature-ideen.md).
const LONG_OFFLINE_FILTER_DAYS = 30;

const FILTERS = [
  { key: "alle", label: "Alle", icon: "mdi:format-list-bulleted" },
  { key: "aktiv", label: "Aktiv", icon: "mdi:lan-connect" },
  { key: "inaktiv", label: "Inaktiv", icon: "mdi:lan-disconnect" },
  { key: "gast", label: "Gast", icon: "mdi:account-question" },
  { key: "gesperrt", label: "Gesperrt", icon: "mdi:web-off" },
  { key: "update", label: "Update", icon: "mdi:package-down" },
  { key: "fest", label: "Feste IP", icon: "mdi:ip-network-outline" },
  { key: "neu", label: "Neu (7 Tage)", icon: "mdi:new-box" },
  { key: "lange_offline", label: "Lange offline", icon: "mdi:clock-remove-outline" },
];

/**
 * Übersetzungen der sichtbaren Karten-Beschriftungen. Ausgewählt wird
 * anhand der in Home Assistant eingestellten Sprache (Fallback Deutsch).
 * Fehlt ein Schlüssel in einer Sprache, wird auf Deutsch zurückgefallen,
 * damit nie ein leeres Feld entsteht.
 */
const I18N = {
  de: {
    "col.name": "Gerät", "col.ip": "IP-Adresse", "col.mac": "MAC-Adresse",
    "col.connection": "Verbindung", "col.ha_name": "Home Assistant",
    "col.ip_type": "IP-Typ", "col.wan": "Internet", "col.update": "Update",
    "col.speed": "Tempo", "col.model": "Modell", "col.type": "Gerätetyp",
    "col.last_seen": "Zuletzt online", "col.status": "Status", "col.vendor": "Hersteller", "col.band": "Funkband",
    "col.connected_via": "Verbunden über",
    "col.label": "Etikett",
    "col.note": "Notiz",
    "field.label": "Etikett",
    "field.note": "Notiz",
    "field.reserved": "Reserviert",
    "note.label_placeholder": "Etikett (z. B. Kinderzimmer)",
    "note.text_placeholder": "Notiz (nur in Home Assistant gespeichert)",
    "note.reserved": "In der FRITZ!Box reserviert",
    "note.reserved_yes": "ja (manuell markiert)",
    "note.reserved_hint": "Die FRITZ!Box meldet Reservierungen innerhalb des DHCP-Bereichs nicht. Mit dieser Markierung zählt das Gerät als „fest“.",
    "btn.edit_note": "Etikett und Notiz bearbeiten",
    "btn.csv": "CSV",
    "btn.csv_tip": "Sichtbare Liste als CSV-Datei speichern",
    "csv.copied": "Download nicht möglich – CSV in die Zwischenablage kopiert",
    "csv.failed": "CSV konnte nicht erstellt werden",
    "group.none": "Nicht gruppieren",
    "group.aria": "Gruppieren nach",
    "group.state": "Gruppieren: Status",
    "group.connection": "Gruppieren: Verbindung",
    "group.vendor": "Gruppieren: Hersteller",
    "group.band": "Gruppieren: Funkband",
    "group.subnet": "Gruppieren: IP-Bereich",
    "group.label": "Gruppieren: Etikett",
    "group.empty.connection": "Ohne Angabe",
    "group.empty.band": "Ohne Funkband",
    "group.empty.vendor": "Hersteller unbekannt",
    "group.empty.subnet": "Ohne IP-Adresse",
    "group.empty.label": "Ohne Etikett",
    "flt.alle": "Alle", "flt.aktiv": "Aktiv", "flt.inaktiv": "Inaktiv",
    "flt.gast": "Gast", "flt.gesperrt": "Gesperrt", "flt.update": "Update", "flt.fest": "Feste IP", "flt.neu": "Neu (7 Tage)", "flt.lange_offline": "Lange offline",
    "search.placeholder": "Name, IP oder MAC", "search.aria": "Geräte durchsuchen",
    "empty.none": "Keine Geräte gefunden.",
    "empty.sensor": "Der Sensor {entity} ist nicht verfügbar.",
    "sum.devices": "{n} Geräte", "sum.active": "{n} aktiv",
    "sum.updates": "{n} mit Update", "sum.blocked": "{n} gesperrt",
    "sum.shown": "{n} angezeigt",
    "state.connected": "Verbunden", "state.disconnected": "Nicht verbunden",
    "state.online_now": "jetzt online", "state.now_online": "gerade online",
    "ls.just_now": "gerade eben", "ls.min": "vor {n} min", "ls.hour": "vor {n} h",
    "ls.yesterday": "gestern", "ls.days": "vor {n} Tagen",
    "iptype.fixed": "fest", "iptype.dynamic": "dynamisch", "iptype.dyn_short": "dyn.", "iptype.noip": "Gerät ohne IP-Adresse", "iptype.static": "statisch", "iptype.dhcp": "DHCP",
    "wan.blocked": "gesperrt", "wan.allowed": "erlaubt",
    "upd.available": "verfügbar", "upd.none": "keines",
    "badge.guest": "Gast", "badge.vpn": "VPN", "badge.priority": "Priorität",
    "badge.mesh": "Mesh-fähig",
    "field.name": "Gerätename", "field.status": "Status", "field.ip_type": "IP-Typ",
    "field.speed": "Tempo", "field.wan": "Internetzugang",
    "field.filter_profile": "Filterprofil", "field.update": "Firmware-Update",
    "field.model": "Modell", "field.type": "Gerätetyp", "field.hostname": "Hostname",
    "field.features": "Merkmale", "field.ha": "Home Assistant",
    "field.last_seen": "Zuletzt online",
    "btn.web": "Weboberfläche öffnen", "btn.ha": "In Home Assistant öffnen",
    "btn.block": "Internet sperren", "btn.unblock": "Internet freigeben",
    "btn.wol": "Aufwecken (WoL)", "btn.close": "Schließen",
    "btn.rename": "Umbenennen", "btn.save": "Speichern", "btn.cancel": "Abbrechen",
    "btn.copy_list": "Namen/MAC-Adressen kopieren",
    "act.blocking": "Sperre …", "act.unblocking": "Gebe frei …",
    "act.blocked": "Gesperrt", "act.unblocked": "Freigegeben",
    "act.failed": "Fehlgeschlagen", "act.wol_sent": "Signal gesendet",
    "act.wol_wait": "…", "copy.aria": "{label} kopieren",
    "popup.gone": "Dieses Gerät ist nicht mehr in der Liste.",
    "popup.aria": "Gerätedetails {name}",
    "tip.web": "Weboberfläche öffnen ({url})", "tip.ha": "Zum Home-Assistant-Gerät",
    "tip.blocked": "Internetzugang gesperrt", "tip.update": "Firmware-Update verfügbar",
    "tip.online": "Gerät ist gerade online",
    "tip.ls_unknown": "Seit Installation der Integration nicht als online erfasst",
    "tip.ls_last": "Zuletzt online: {ts}", "tip.sort": "Nach {label} sortieren",
    "arrow.left": "Nach links blättern", "arrow.right": "Nach rechts blättern",
    "ctl.mesh": "Mesh", "ctl.mesh_online": "{online} von {total} online", "ctl.mesh_reboot": "Alle neu starten", "ctl.mesh_reboot_confirm": "Alle wirklich neu starten?", "ctl.mesh_reboot_tip": "FRITZ!Box und alle Repeater neu starten (erst die Repeater, dann die Box)", "ctl.throughput": "Aktueller Durchsatz (Download / Upload)", "ctl.wlan_24": "WLAN 2,4 GHz", "ctl.wlan_5": "WLAN 5 GHz", "ctl.wlan_guest": "Gast-WLAN", "ctl.reconnect": "Neu verbinden", "ctl.reconnect_confirm": "Wirklich neu verbinden?", "ctl.reboot": "Neustart", "ctl.reboot_confirm": "Wirklich neu starten?", "ctl.mac_filter": "MAC-Filter", "ctl.mac_filter_tip": "WLAN-Zugang auf bekannte Geräte beschränken", "ctl.pairing": "Pairing starten", "ctl.pairing_confirm": "Wirklich starten?", "ctl.pairing_tip": "MAC-Filter kurz ausschalten, damit sich ein neues Gerät anmelden kann", "ctl.pairing_until": "Pairing bis {time}", "ctl.pairing_end_tip": "Klicken: Filter sofort wieder einschalten", "ctl.gast_wlan_qr": "QR-Code", "ctl.gast_wlan_qr_tip": "Gast-WLAN: SSID, Passwort und QR-Code zum Verbinden anzeigen", "gwlan.title": "Gast-WLAN", "gwlan.loading": "Lade Zugangsdaten …", "gwlan.ssid": "Netzwerkname (SSID)", "gwlan.password": "Passwort", "gwlan.open_network": "Offenes Netz – kein Passwort nötig", "gwlan.scan_hint": "Mit der Smartphone-Kamera scannen, um sich automatisch mit dem Gast-WLAN zu verbinden.", "gwlan.disabled_hint": "Das Gast-WLAN ist derzeit ausgeschaltet. Der QR-Code funktioniert, sobald es wieder eingeschaltet ist.", "gwlan.error": "Zugangsdaten konnten nicht geladen werden: {error}",
    "ver.title": "Installierte Version der Integration", "ver.update": "Update {version}", "ver.update_tip": "Neue Version {version} verfügbar – klicken für die Release-Notizen", "ver.update_plain_tip": "Neue Version {version} verfügbar", "ver.card_mismatch": "Karte {card} ≠ Integration {integration} – Seite neu laden (Strg+F5)", "ver.checked": "Zuletzt geprüft: {time}",
    "prof.title": "Zugangsprofil", "prof.load": "Anzeigen", "prof.load_tip": "Aktuelles Zugangsprofil aus der FRITZ!Box laden (Kindersicherung, experimentell)", "prof.loading": "Lade …", "prof.current": "Aktuell: {name}", "prof.apply": "Übernehmen", "prof.apply_tip": "Ausgewähltes Zugangsprofil dem Gerät zuweisen", "prof.minutes": "Minuten (optional)", "prof.minutes_hint": "Mit Minuten gilt das Profil nur so lange, danach wird das bisherige Profil wiederhergestellt.", "prof.revert": "Zurück auf {name} um {time}", "prof.error": "Zugangsprofil: {error}", "prof.saved": "Zugangsprofil geändert: {name}", "prof.warn": "Experimentell – läuft über die Weboberfläche der Box", "prof.unknown": "unbekannt", "prof.retry": "Erneut versuchen",
    "field.tracker": "Anwesenheit", "tracker.home": "zuhause", "tracker.away": "abwesend", "tracker.open": "Tracker öffnen",
    "tracker.unknown": "unbekannt", "tracker.disabled": "Entität deaktiviert",
    "tracker.disabled_hint": "Die Tracker-Entität ist in Home Assistant deaktiviert – hier klicken und im Zahnrad-Dialog aktivieren.",
    "tracker.off": "nicht aktiviert",
    "tracker.off_hint": "Device Tracker einschalten unter: Einstellungen → Geräte & Dienste → FRITZ!Box Netzwerk → Konfigurieren.", "tab.network": "Netzwerk", "tab.controls": "Steuerung",
    "field.band": "Funkband", "band.24": "2,4 GHz", "band.5": "5 GHz", "band.6": "6 GHz",
    "field.connected_via": "Verbunden über",
    "field.vendor": "Hersteller", "vendor.random": "Zufällige MAC",
    "vendor.random_tip": "Zufällige (private) MAC-Adresse – meist die „Private WLAN-Adresse“ eines Smartphones oder Tablets. Einen Hersteller kann man daraus nicht ablesen.",
    "tip.copy": "Klicken zum Kopieren", "copy.done": "{value} kopiert",
    "copy.failed": "Kopieren nicht möglich – bitte den Wert markieren und mit Strg+C kopieren.",
  },
  en: {
    "col.name": "Device", "col.ip": "IP address", "col.mac": "MAC address",
    "col.connection": "Connection", "col.ha_name": "Home Assistant",
    "col.ip_type": "IP type", "col.wan": "Internet", "col.update": "Update",
    "col.speed": "Speed", "col.model": "Model", "col.type": "Device type",
    "col.last_seen": "Last seen", "col.status": "Status", "col.vendor": "Manufacturer", "col.band": "Wi-Fi band",
    "col.connected_via": "Connected via",
    "col.label": "Label",
    "col.note": "Note",
    "field.label": "Label",
    "field.note": "Note",
    "field.reserved": "Reserved",
    "note.label_placeholder": "Label (e.g. Kids room)",
    "note.text_placeholder": "Note (stored in Home Assistant only)",
    "note.reserved": "Reserved in the FRITZ!Box",
    "note.reserved_yes": "yes (marked manually)",
    "note.reserved_hint": "The FRITZ!Box does not report reservations inside the DHCP range. With this mark the device counts as \"fixed\".",
    "btn.edit_note": "Edit label and note",
    "btn.csv": "CSV",
    "btn.csv_tip": "Save the visible list as a CSV file",
    "csv.copied": "Download not possible – CSV copied to the clipboard",
    "csv.failed": "Could not create the CSV",
    "group.none": "No grouping",
    "group.aria": "Group by",
    "group.state": "Group: status",
    "group.connection": "Group: connection",
    "group.vendor": "Group: manufacturer",
    "group.band": "Group: Wi-Fi band",
    "group.subnet": "Group: IP range",
    "group.label": "Group: label",
    "group.empty.connection": "Not specified",
    "group.empty.band": "No Wi-Fi band",
    "group.empty.vendor": "Manufacturer unknown",
    "group.empty.subnet": "No IP address",
    "group.empty.label": "No label",
    "flt.alle": "All", "flt.aktiv": "Active", "flt.inaktiv": "Inactive",
    "flt.gast": "Guest", "flt.gesperrt": "Blocked", "flt.update": "Update", "flt.fest": "Fixed IP", "flt.neu": "New (7 days)", "flt.lange_offline": "Long offline",
    "search.placeholder": "Name, IP or MAC", "search.aria": "Search devices",
    "empty.none": "No devices found.",
    "empty.sensor": "The sensor {entity} is unavailable.",
    "sum.devices": "{n} devices", "sum.active": "{n} active",
    "sum.updates": "{n} with update", "sum.blocked": "{n} blocked",
    "sum.shown": "{n} shown",
    "state.connected": "Connected", "state.disconnected": "Not connected",
    "state.online_now": "online now", "state.now_online": "online now",
    "ls.just_now": "just now", "ls.min": "{n} min ago", "ls.hour": "{n} h ago",
    "ls.yesterday": "yesterday", "ls.days": "{n} days ago",
    "iptype.fixed": "fixed", "iptype.dynamic": "dynamic", "iptype.dyn_short": "dyn.", "iptype.noip": "Device without IP address", "iptype.static": "static", "iptype.dhcp": "DHCP",
    "wan.blocked": "blocked", "wan.allowed": "allowed",
    "upd.available": "available", "upd.none": "none",
    "badge.guest": "Guest", "badge.vpn": "VPN", "badge.priority": "Priority",
    "badge.mesh": "Mesh-capable",
    "field.name": "Device name", "field.status": "Status", "field.ip_type": "IP type",
    "field.speed": "Speed", "field.wan": "Internet access",
    "field.filter_profile": "Filter profile", "field.update": "Firmware update",
    "field.model": "Model", "field.type": "Device type", "field.hostname": "Hostname",
    "field.features": "Features", "field.ha": "Home Assistant",
    "field.last_seen": "Last seen",
    "btn.web": "Open web interface", "btn.ha": "Open in Home Assistant",
    "btn.block": "Block internet", "btn.unblock": "Allow internet",
    "btn.wol": "Wake (WoL)", "btn.close": "Close",
    "btn.rename": "Rename", "btn.save": "Save", "btn.cancel": "Cancel",
    "btn.copy_list": "Copy names/MAC addresses",
    "act.blocking": "Blocking …", "act.unblocking": "Allowing …",
    "act.blocked": "Blocked", "act.unblocked": "Allowed",
    "act.failed": "Failed", "act.wol_sent": "Signal sent",
    "act.wol_wait": "…", "copy.aria": "Copy {label}",
    "popup.gone": "This device is no longer in the list.",
    "popup.aria": "Device details {name}",
    "tip.web": "Open web interface ({url})", "tip.ha": "Go to Home Assistant device",
    "tip.blocked": "Internet access blocked", "tip.update": "Firmware update available",
    "tip.online": "Device is currently online",
    "tip.ls_unknown": "Not seen online since the integration was installed",
    "tip.ls_last": "Last seen: {ts}", "tip.sort": "Sort by {label}",
    "arrow.left": "Scroll left", "arrow.right": "Scroll right",
    "ctl.mesh": "Mesh", "ctl.mesh_online": "{online} of {total} online", "ctl.mesh_reboot": "Restart all", "ctl.mesh_reboot_confirm": "Really restart all?", "ctl.mesh_reboot_tip": "Restart the FRITZ!Box and all repeaters (repeaters first, then the box)", "ctl.throughput": "Current throughput (download / upload)", "ctl.wlan_24": "Wi-Fi 2.4 GHz", "ctl.wlan_5": "Wi-Fi 5 GHz", "ctl.wlan_guest": "Guest Wi-Fi", "ctl.reconnect": "Reconnect", "ctl.reconnect_confirm": "Really reconnect?", "ctl.reboot": "Reboot", "ctl.reboot_confirm": "Really reboot?", "ctl.mac_filter": "MAC filter", "ctl.mac_filter_tip": "Restrict Wi-Fi access to known devices", "ctl.pairing": "Start pairing", "ctl.pairing_confirm": "Really start?", "ctl.pairing_tip": "Turn the MAC filter off briefly so a new device can join", "ctl.pairing_until": "Pairing until {time}", "ctl.pairing_end_tip": "Click: turn the filter back on now", "ctl.gast_wlan_qr": "QR code", "ctl.gast_wlan_qr_tip": "Guest Wi-Fi: show SSID, password and a QR code to connect", "gwlan.title": "Guest Wi-Fi", "gwlan.loading": "Loading credentials …", "gwlan.ssid": "Network name (SSID)", "gwlan.password": "Password", "gwlan.open_network": "Open network – no password needed", "gwlan.scan_hint": "Scan with your phone's camera to connect to the guest Wi-Fi automatically.", "gwlan.disabled_hint": "The guest Wi-Fi is currently switched off. The QR code will work again once it's switched back on.", "gwlan.error": "Could not load the guest Wi-Fi credentials: {error}",
    "ver.title": "Installed version of the integration", "ver.update": "Update {version}", "ver.update_tip": "New version {version} available – click for the release notes", "ver.update_plain_tip": "New version {version} available", "ver.card_mismatch": "Card {card} ≠ integration {integration} – reload the page (Ctrl+F5)", "ver.checked": "Last checked: {time}",
    "prof.title": "Access profile", "prof.load": "Show", "prof.load_tip": "Load the current access profile from the FRITZ!Box (parental control, experimental)", "prof.loading": "Loading …", "prof.current": "Current: {name}", "prof.apply": "Apply", "prof.apply_tip": "Assign the selected access profile to the device", "prof.minutes": "Minutes (optional)", "prof.minutes_hint": "With minutes the profile only applies that long, then the previous profile is restored.", "prof.revert": "Back to {name} at {time}", "prof.error": "Access profile: {error}", "prof.saved": "Access profile changed: {name}", "prof.warn": "Experimental – uses the box web interface", "prof.unknown": "unknown", "prof.retry": "Try again",
    "field.tracker": "Presence", "tracker.home": "home", "tracker.away": "away", "tracker.open": "Open tracker",
    "tracker.unknown": "unknown", "tracker.disabled": "entity disabled",
    "tracker.disabled_hint": "The tracker entity is disabled in Home Assistant – click here and enable it in the settings dialog.",
    "tracker.off": "not enabled",
    "tracker.off_hint": "Enable the device tracker under: Settings → Devices & services → FRITZ!Box Netzwerk → Configure.", "tab.network": "Network", "tab.controls": "Controls",
    "field.band": "Wi-Fi band", "band.24": "2.4 GHz", "band.5": "5 GHz", "band.6": "6 GHz",
    "field.connected_via": "Connected via",
    "field.vendor": "Manufacturer", "vendor.random": "Random MAC",
    "vendor.random_tip": "Random (private) MAC address \u2013 usually the \u201cPrivate Wi-Fi address\u201d of a smartphone or tablet. No manufacturer can be derived from it.",
    "tip.copy": "Click to copy", "copy.done": "{value} copied",
    "copy.failed": "Copying is not possible \u2013 please select the value and copy it with Ctrl+C.",
  },
  nl: {
    "col.name": "Apparaat", "col.ip": "IP-adres", "col.mac": "MAC-adres",
    "col.connection": "Verbinding", "col.ha_name": "Home Assistant",
    "col.ip_type": "IP-type", "col.wan": "Internet", "col.update": "Update",
    "col.speed": "Snelheid", "col.model": "Model", "col.type": "Apparaattype",
    "col.last_seen": "Laatst online", "col.status": "Status", "col.vendor": "Fabrikant", "col.band": "Wifi-band",
    "col.connected_via": "Verbonden via",
    "col.label": "Label",
    "col.note": "Notitie",
    "field.label": "Label",
    "field.note": "Notitie",
    "field.reserved": "Gereserveerd",
    "note.label_placeholder": "Label (bijv. Kinderkamer)",
    "note.text_placeholder": "Notitie (alleen in Home Assistant opgeslagen)",
    "note.reserved": "Gereserveerd in de FRITZ!Box",
    "note.reserved_yes": "ja (handmatig gemarkeerd)",
    "note.reserved_hint": "De FRITZ!Box meldt geen reserveringen binnen het DHCP-bereik. Met deze markering telt het apparaat als \"vast\".",
    "btn.edit_note": "Label en notitie bewerken",
    "btn.csv": "CSV",
    "btn.csv_tip": "Zichtbare lijst als CSV-bestand opslaan",
    "csv.copied": "Downloaden niet mogelijk – CSV naar het klembord gekopieerd",
    "csv.failed": "CSV kon niet worden gemaakt",
    "group.none": "Niet groeperen",
    "group.aria": "Groeperen op",
    "group.state": "Groeperen: status",
    "group.connection": "Groeperen: verbinding",
    "group.vendor": "Groeperen: fabrikant",
    "group.band": "Groeperen: wifi-band",
    "group.subnet": "Groeperen: IP-bereik",
    "group.label": "Groeperen: label",
    "group.empty.connection": "Niet opgegeven",
    "group.empty.band": "Geen wifi-band",
    "group.empty.vendor": "Fabrikant onbekend",
    "group.empty.subnet": "Geen IP-adres",
    "group.empty.label": "Geen label",
    "flt.alle": "Alle", "flt.aktiv": "Actief", "flt.inaktiv": "Inactief",
    "flt.gast": "Gast", "flt.gesperrt": "Geblokkeerd", "flt.update": "Update", "flt.fest": "Vast IP", "flt.neu": "Nieuw (7 dagen)", "flt.lange_offline": "Lang offline",
    "search.placeholder": "Naam, IP of MAC", "search.aria": "Apparaten zoeken",
    "empty.none": "Geen apparaten gevonden.",
    "empty.sensor": "De sensor {entity} is niet beschikbaar.",
    "sum.devices": "{n} apparaten", "sum.active": "{n} actief",
    "sum.updates": "{n} met update", "sum.blocked": "{n} geblokkeerd",
    "sum.shown": "{n} weergegeven",
    "state.connected": "Verbonden", "state.disconnected": "Niet verbonden",
    "state.online_now": "nu online", "state.now_online": "nu online",
    "ls.just_now": "zojuist", "ls.min": "{n} min geleden", "ls.hour": "{n} u geleden",
    "ls.yesterday": "gisteren", "ls.days": "{n} dagen geleden",
    "iptype.fixed": "vast", "iptype.dynamic": "dynamisch", "iptype.dyn_short": "dyn.", "iptype.noip": "Apparaat zonder IP-adres", "iptype.static": "statisch", "iptype.dhcp": "DHCP",
    "wan.blocked": "geblokkeerd", "wan.allowed": "toegestaan",
    "upd.available": "beschikbaar", "upd.none": "geen",
    "badge.guest": "Gast", "badge.vpn": "VPN", "badge.priority": "Prioriteit",
    "badge.mesh": "Mesh-geschikt",
    "field.name": "Apparaatnaam", "field.status": "Status", "field.ip_type": "IP-type",
    "field.speed": "Snelheid", "field.wan": "Internettoegang",
    "field.filter_profile": "Filterprofiel", "field.update": "Firmware-update",
    "field.model": "Model", "field.type": "Apparaattype", "field.hostname": "Hostnaam",
    "field.features": "Kenmerken", "field.ha": "Home Assistant",
    "field.last_seen": "Laatst online",
    "btn.web": "Webinterface openen", "btn.ha": "In Home Assistant openen",
    "btn.block": "Internet blokkeren", "btn.unblock": "Internet toestaan",
    "btn.wol": "Wekken (WoL)", "btn.close": "Sluiten",
    "btn.rename": "Naam wijzigen", "btn.save": "Opslaan", "btn.cancel": "Annuleren",
    "btn.copy_list": "Namen/MAC-adressen kopiëren",
    "act.blocking": "Blokkeren …", "act.unblocking": "Toestaan …",
    "act.blocked": "Geblokkeerd", "act.unblocked": "Toegestaan",
    "act.failed": "Mislukt", "act.wol_sent": "Signaal verzonden",
    "act.wol_wait": "…", "copy.aria": "{label} kopiëren",
    "popup.gone": "Dit apparaat staat niet meer in de lijst.",
    "popup.aria": "Apparaatdetails {name}",
    "tip.web": "Webinterface openen ({url})", "tip.ha": "Naar Home Assistant-apparaat",
    "tip.blocked": "Internettoegang geblokkeerd", "tip.update": "Firmware-update beschikbaar",
    "tip.online": "Apparaat is nu online",
    "tip.ls_unknown": "Sinds installatie van de integratie niet online gezien",
    "tip.ls_last": "Laatst online: {ts}", "tip.sort": "Sorteren op {label}",
    "arrow.left": "Naar links bladeren", "arrow.right": "Naar rechts bladeren",
    "ctl.mesh": "Mesh", "ctl.mesh_online": "{online} van {total} online", "ctl.mesh_reboot": "Alles herstarten", "ctl.mesh_reboot_confirm": "Echt alles herstarten?", "ctl.mesh_reboot_tip": "FRITZ!Box en alle repeaters herstarten (eerst de repeaters, dan de box)", "ctl.throughput": "Huidige doorvoer (download / upload)", "ctl.wlan_24": "Wifi 2,4 GHz", "ctl.wlan_5": "Wifi 5 GHz", "ctl.wlan_guest": "Gast-wifi", "ctl.reconnect": "Opnieuw verbinden", "ctl.reconnect_confirm": "Echt opnieuw verbinden?", "ctl.reboot": "Herstart", "ctl.reboot_confirm": "Echt herstarten?", "ctl.mac_filter": "MAC-filter", "ctl.mac_filter_tip": "Wifi-toegang beperken tot bekende apparaten", "ctl.pairing": "Koppelen starten", "ctl.pairing_confirm": "Echt starten?", "ctl.pairing_tip": "MAC-filter kort uitschakelen zodat een nieuw apparaat zich kan aanmelden", "ctl.pairing_until": "Koppelen tot {time}", "ctl.pairing_end_tip": "Klik: filter meteen weer inschakelen", "ctl.gast_wlan_qr": "QR-code", "ctl.gast_wlan_qr_tip": "Gast-wifi: SSID, wachtwoord en een QR-code om te verbinden tonen", "gwlan.title": "Gast-wifi", "gwlan.loading": "Gegevens laden …", "gwlan.ssid": "Netwerknaam (SSID)", "gwlan.password": "Wachtwoord", "gwlan.open_network": "Open netwerk – geen wachtwoord nodig", "gwlan.scan_hint": "Scan met de camera van je telefoon om automatisch met het gastennetwerk te verbinden.", "gwlan.disabled_hint": "Het gastennetwerk staat momenteel uit. De QR-code werkt weer zodra het is ingeschakeld.", "gwlan.error": "Gegevens konden niet worden geladen: {error}",
    "ver.title": "Geïnstalleerde versie van de integratie", "ver.update": "Update {version}", "ver.update_tip": "Nieuwe versie {version} beschikbaar – klik voor de release-notities", "ver.update_plain_tip": "Nieuwe versie {version} beschikbaar", "ver.card_mismatch": "Kaart {card} ≠ integratie {integration} – pagina opnieuw laden (Ctrl+F5)", "ver.checked": "Laatst gecontroleerd: {time}",
    "prof.title": "Toegangsprofiel", "prof.load": "Tonen", "prof.load_tip": "Huidig toegangsprofiel uit de FRITZ!Box laden (ouderlijk toezicht, experimenteel)", "prof.loading": "Laden …", "prof.current": "Huidig: {name}", "prof.apply": "Toepassen", "prof.apply_tip": "Geselecteerd toegangsprofiel aan het apparaat toewijzen", "prof.minutes": "Minuten (optioneel)", "prof.minutes_hint": "Met minuten geldt het profiel slechts zo lang, daarna wordt het vorige profiel hersteld.", "prof.revert": "Terug naar {name} om {time}", "prof.error": "Toegangsprofiel: {error}", "prof.saved": "Toegangsprofiel gewijzigd: {name}", "prof.warn": "Experimenteel – via de webinterface van de box", "prof.unknown": "onbekend", "prof.retry": "Opnieuw proberen",
    "field.tracker": "Aanwezigheid", "tracker.home": "thuis", "tracker.away": "afwezig", "tracker.open": "Tracker openen",
    "tracker.unknown": "onbekend", "tracker.disabled": "entiteit uitgeschakeld",
    "tracker.disabled_hint": "De trackerentiteit is uitgeschakeld in Home Assistant – klik hier en schakel deze in via het instellingenvenster.",
    "tracker.off": "niet ingeschakeld",
    "tracker.off_hint": "Device tracker inschakelen via: Instellingen → Apparaten & diensten → FRITZ!Box Netzwerk → Configureren.", "tab.network": "Netwerk", "tab.controls": "Bediening",
    "field.band": "Wifi-band", "band.24": "2,4 GHz", "band.5": "5 GHz", "band.6": "6 GHz",
    "field.connected_via": "Verbonden via",
    "field.vendor": "Fabrikant", "vendor.random": "Willekeurig MAC",
    "vendor.random_tip": "Willekeurig (privé) MAC-adres \u2013 meestal het \u201cPrivé wifi-adres\u201d van een smartphone of tablet. Er is geen fabrikant uit af te leiden.",
    "tip.copy": "Klik om te kopiëren", "copy.done": "{value} gekopieerd",
    "copy.failed": "Kopiëren niet mogelijk \u2013 selecteer de waarde en kopieer met Ctrl+C.",
  },
};

const SUPPORTED_LANGS = ["de", "en", "nl"];

/** Ermittelt die anzuzeigende Sprache aus Konfig oder HA-Spracheinstellung. */
function resolveLang(config, hass) {
  const wanted = String(
    (config && config.language) ||
      (hass && hass.locale && hass.locale.language) ||
      (hass && hass.language) ||
      "de"
  )
    .slice(0, 2)
    .toLowerCase();
  return SUPPORTED_LANGS.includes(wanted) ? wanted : "de";
}

/** Übersetzt einen Schlüssel und ersetzt {platzhalter}. */
function translate(lang, key, params) {
  const table = I18N[lang] || I18N.de;
  let text = table[key];
  if (text === undefined) text = I18N.de[key];
  if (text === undefined) return key;
  if (params) {
    for (const name of Object.keys(params)) {
      text = text.replace(new RegExp(`\\{${name}\\}`, "g"), String(params[name]));
    }
  }
  return text;
}

/** Standardfarbe je Farbschluessel, wenn der Nutzer nichts gesetzt hat. */
const COLOR_FALLBACKS = {
  color_header_bg: "var(--table-row-alternative-background-color, var(--secondary-background-color))",
  color_header_text: "var(--secondary-text-color)",
  color_row_text: "var(--primary-text-color)",
  color_row_alt_bg: "transparent",
  color_border: "var(--divider-color)",
  color_active: "var(--success-color, #43a047)",
  color_inactive: "var(--disabled-text-color, #9e9e9e)",
  color_guest: "var(--warning-color, #ffa600)",
  color_blocked: "var(--error-color, #db4437)",
  color_update: "var(--info-color, #039be5)",
  color_static: "var(--primary-color)",
  color_accent: "var(--primary-color)",
  // Kategorie-Symbolfarben: standardmäßig "inherit" (= Chip-Textfarbe/Akzent).
  color_cat_alle: "inherit",
  color_cat_aktiv: "inherit",
  color_cat_inaktiv: "inherit",
  color_cat_gast: "inherit",
  color_cat_gesperrt: "inherit",
  color_cat_update: "inherit",
  color_cat_fest: "inherit",
  color_cat_neu: "inherit",
  color_cat_lange_offline: "inherit",
};

const COLOR_EDITOR_FIELDS = [
  { key: "color_header_bg", label: "Kopfzeile Hintergrund" },
  { key: "color_header_text", label: "Kopfzeile Schrift" },
  { key: "color_row_text", label: "Zeilen Schrift" },
  { key: "color_row_alt_bg", label: "Jede zweite Zeile" },
  { key: "color_border", label: "Trennlinien" },
  { key: "color_active", label: "Aktiv" },
  { key: "color_inactive", label: "Inaktiv" },
  { key: "color_guest", label: "Gastnetz" },
  { key: "color_blocked", label: "Gesperrt" },
  { key: "color_update", label: "Update verfügbar" },
  { key: "color_static", label: "Statische IP" },
  { key: "color_accent", label: "Akzent (Sortierung, Filter)" },
  { key: "color_cat_alle", label: "Symbol Kategorie „Alle“" },
  { key: "color_cat_aktiv", label: "Symbol Kategorie „Aktiv“" },
  { key: "color_cat_inaktiv", label: "Symbol Kategorie „Inaktiv“" },
  { key: "color_cat_gast", label: "Symbol Kategorie „Gast“" },
  { key: "color_cat_gesperrt", label: "Symbol Kategorie „Gesperrt“" },
  { key: "color_cat_update", label: "Symbol Kategorie „Update“" },
  { key: "color_cat_fest", label: "Symbol Kategorie „Feste IP“" },
  { key: "color_cat_neu", label: "Symbol Kategorie „Neu“" },
  { key: "color_cat_lange_offline", label: "Symbol Kategorie „Lange offline“" },
];

/* ------------------------------------------------------------------ */
/* Hilfsfunktionen                                                     */
/* ------------------------------------------------------------------ */

/** Fuellt fehlende Schluessel mit den Standardwerten auf. */
function withDefaults(config) {
  return { ...CONFIG_DEFAULTS, ...(config || {}) };
}

/**
 * Laesst nur Farbwerte durch, die sicher in eine CSS-Variable koennen.
 * Alles mit ; < > { } ( ) ausserhalb von rgb/hsl/var oder mit url()
 * wird verworfen - so kann ueber die Kartenkonfiguration kein fremdes
 * CSS eingeschleust werden.
 */
function sanitizeColor(value) {
  if (typeof value !== "string") return "";
  const text = value.trim();
  if (!text) return "";
  if (text.length > 120) return "";
  if (/[;<>{}\\]/.test(text)) return "";
  if (/url\s*\(|expression|@import|javascript:/i.test(text)) return "";
  if (/^#[0-9a-f]{3,8}$/i.test(text)) return text;
  if (/^[a-z][a-z0-9-]*$/i.test(text)) return text;
  if (/^(rgb|rgba|hsl|hsla|var|color-mix)\([^()]*(\([^()]*\))?[^()]*\)$/i.test(text)) {
    return text;
  }
  return "";
}

const HEX_COLOR_RE = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i;

/** Wandelt Kurzschreibweisen wie #abc in #aabbcc, sonst leer. */
function normalizeHex(value) {
  if (typeof value !== "string" || !HEX_COLOR_RE.test(value.trim())) return "";
  let hex = value.trim().toLowerCase();
  if (hex.length === 4) {
    hex = "#" + hex[1] + hex[1] + hex[2] + hex[2] + hex[3] + hex[3];
  }
  return hex;
}

/** Maskiert Text, der aus der FRITZ!Box stammt, vor der HTML-Ausgabe. */
function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Kopiert Text in die Zwischenablage; liefert ein Promise<boolean>.
 *
 * Die moderne Zwischenablage-API (navigator.clipboard) gibt es nur in
 * "sicheren Kontexten" (HTTPS oder localhost). Wer Home Assistant per
 * http://192.168.x.x:8123 aufruft, hat sie nicht - dort schlug das Kopieren
 * bis 1.6.0b0 stumm fehl. Deshalb der Rueckfall ueber ein verstecktes
 * Textfeld und document.execCommand("copy"). Der Rueckfall laeuft
 * SYNCHRON (ohne vorheriges await), weil Safari ihn nur innerhalb der
 * Klick-Behandlung erlaubt.
 */
async function copyToClipboard(text, container) {
  const value = String(text ?? "");
  if (!value) return false;
  const api = typeof navigator !== "undefined" ? navigator.clipboard : null;
  if (api && typeof api.writeText === "function" && window.isSecureContext !== false) {
    try {
      await api.writeText(value);
      return true;
    } catch (err) {
      // Berechtigung verweigert o. ä. - weiter mit dem Rueckfall.
    }
  }
  return legacyCopy(value, container);
}

/** Rueckfall: Text in ein verstecktes Feld setzen, markieren, "copy". */
function legacyCopy(value, container) {
  const active = document.activeElement;
  const area = document.createElement("textarea");
  area.value = value;
  area.setAttribute("readonly", "");
  area.setAttribute("aria-hidden", "true");
  area.style.cssText =
    "position:fixed;top:0;left:0;width:1px;height:1px;padding:0;border:0;opacity:0;pointer-events:none;";
  (container || document.body).appendChild(area);
  let ok = false;
  try {
    area.focus({ preventScroll: true });
    area.select();
    area.setSelectionRange(0, value.length);
    ok = typeof document.execCommand === "function" && document.execCommand("copy") === true;
  } catch (err) {
    ok = false;
  }
  area.remove();
  try {
    if (active && typeof active.focus === "function") active.focus({ preventScroll: true });
  } catch (err) {
    // Fokus konnte nicht zurueckgegeben werden - unkritisch.
  }
  return ok;
}

/**
 * Wandelt ein Muster mit Platzhaltern in einen regulaeren Ausdruck um:
 * "*" = beliebig viele Zeichen, "?" = genau ein Zeichen. Alles andere wird
 * woertlich genommen (der Punkt einer IP-Adresse ist also KEIN Platzhalter).
 * Mit ``anchored`` muss das Muster den ganzen Text treffen (IP-Filter),
 * sonst genuegt ein Treffer irgendwo im Text (Suchfeld).
 */
function wildcardToRegExp(pattern, anchored) {
  const body = String(pattern)
    .replace(/[.+^${}()|[\]\\]/g, "\\$&")
    .replace(/\*/g, ".*")
    .replace(/\?/g, ".");
  return new RegExp(anchored ? `^${body}$` : body, "i");
}

/**
 * Zerlegt die Angabe ``ip_filter`` (Text oder Liste) in Treffer- und
 * Ausschlussmuster. Getrennt wird an Komma, Semikolon und Leerraum; ein
 * fuehrendes "!" macht aus einem Muster einen Ausschluss. Liefert null,
 * wenn nichts zu filtern ist.
 */
function parseIpFilter(value) {
  const text = Array.isArray(value) ? value.join(",") : String(value ?? "");
  const include = [];
  const exclude = [];
  for (const token of text.split(/[\s,;]+/)) {
    if (!token) continue;
    if (token.startsWith("!")) {
      const rest = token.slice(1);
      if (rest) exclude.push(wildcardToRegExp(rest, true));
    } else {
      include.push(wildcardToRegExp(token, true));
    }
  }
  if (include.length === 0 && exclude.length === 0) return null;
  return { include, exclude };
}

/**
 * Prueft eine IP-Adresse gegen einen geparsten Filter. Ohne Treffermuster
 * (nur Ausschluesse) gilt jede Adresse als Treffer, die nicht ausgeschlossen
 * ist. Geraete ohne IP-Adresse fallen bei jedem Treffermuster heraus.
 */
function ipMatchesFilter(ip, filter) {
  if (!filter) return true;
  const text = String(ip || "").trim();
  if (filter.include.length > 0 && !filter.include.some((re) => re.test(text))) {
    return false;
  }
  return !filter.exclude.some((re) => re.test(text));
}

/** Sortierschluessel, der IPv4-Adressen numerisch ordnet. */
function ipSortKey(ip) {
  const parts = String(ip || "").split(".");
  if (parts.length !== 4) return Number.MAX_SAFE_INTEGER;
  let value = 0;
  for (const part of parts) {
    const octet = Number(part);
    if (!Number.isInteger(octet) || octet < 0 || octet > 255) {
      return Number.MAX_SAFE_INTEGER;
    }
    value = value * 256 + octet;
  }
  return value;
}

/** "1000 Mbit/s" bzw. "—" bei unbekanntem Tempo. */
function formatSpeed(speed) {
  const value = Number(speed) || 0;
  if (value <= 0) return "—";
  if (value >= 1000 && value % 1000 === 0) return `${value / 1000} Gbit/s`;
  return `${value} Mbit/s`;
}

/** Kompakte Tempo-Formatierung: "866 M", "1 G" - passt in eine Zeile. */
function formatSpeedCompact(speed) {
  const value = Number(speed) || 0;
  if (value <= 0) return "—";
  if (value >= 1000 && value % 1000 === 0) return `${value / 1000} G`;
  return `${value} M`;
}

/** Datenrate (kByte/s) lesbar: ab 1000 kB/s in MB/s. */
function formatRate(kbytes) {
  if (kbytes === null || kbytes === undefined || kbytes === "") return "—";
  const value = Number(kbytes);
  if (!Number.isFinite(value) || value < 0) return "—";
  if (value >= 1000) return `${(value / 1000).toFixed(1).replace(".", ",")} MB/s`;
  return `${Math.round(value)} kB/s`;
}

/** Restlaufzeit der DHCP-Zuweisung in lesbarer Form. */
function formatLease(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value) || value <= 0) return "";
  if (value < 3600) return `noch ${Math.round(value / 60)} min`;
  if (value < 86400) return `noch ${Math.round(value / 3600)} h`;
  return `noch ${Math.round(value / 86400)} Tage`;
}

/**
 * "Zuletzt online" lesbar aufbereiten: relativ bei kurzer Zeit, sonst
 * Datum. Erwartet einen ISO-Zeitstempel; ohne Wert kommt "—".
 */
function formatLastSeen(iso, lang, now) {
  const L = lang || "de";
  if (!iso) return "—";
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return "—";
  const ref = now || Date.now();
  const diff = Math.max(0, ref - then);
  const min = Math.floor(diff / 60000);
  if (min < 1) return translate(L, "ls.just_now");
  if (min < 60) return translate(L, "ls.min", { n: min });
  const hours = Math.floor(min / 60);
  if (hours < 24) return translate(L, "ls.hour", { n: hours });
  const days = Math.floor(hours / 24);
  if (days === 1) return translate(L, "ls.yesterday");
  if (days < 7) return translate(L, "ls.days", { n: days });
  // Ab einer Woche das konkrete Datum.
  const date = new Date(then);
  const dd = String(date.getDate()).padStart(2, "0");
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  return `${dd}.${mm}.${date.getFullYear()}`;
}

/** Icon je Verbindungsart. */
function connectionIcon(host) {
  if (!host.active) return "mdi:lan-disconnect";
  if (host.connection === "wlan") return "mdi:wifi";
  if (host.connection === "lan") return "mdi:ethernet";
  if (host.connection === "powerline") return "mdi:power-plug";
  return "mdi:help-network-outline";
}

/**
 * Ermittelt die Webadresse eines Geraets fuer den Klick auf die
 * IP-Adresse. Bevorzugt die von der FRITZ!Box gemeldete URL
 * (X_AVM-DE_URL), faellt sonst - falls erlaubt - auf http://<ip> zurueck.
 * Aus Sicherheitsgruenden werden ausschliesslich http/https zugelassen;
 * alles andere (z. B. ein manipuliertes javascript:-Schema) wird
 * verworfen.
 */
function webUrl(host, allowFallback) {
  const raw = String(host.url || "").trim();
  if (/^https?:\/\/\S+$/i.test(raw)) return raw;
  if (allowFallback && host.ip) {
    const ip = String(host.ip).trim();
    // Nur eine plausible IPv4/Hostadresse akzeptieren.
    if (/^[a-z0-9.:_-]+$/i.test(ip)) return `http://${ip}`;
  }
  return "";
}

/** Wert, nach dem eine bestimmte Spalte sortiert wird. */
function sortValue(host, key) {
  switch (key) {
    case "status":
      return host.active ? 0 : 1;
    case "name":
      return String(host.name || "").toLowerCase();
    case "ip":
      return ipSortKey(host.ip);
    case "mac":
      return String(host.mac || "");
    case "vendor":
      // Ohne Hersteller ans Ende; zufällige Adressen vor den ganz unbekannten.
      return host.vendor
        ? `0${String(host.vendor).toLowerCase()}`
        : host.mac_random
        ? "1"
        : "2";
    case "connection":
      return String(host.connection_label || "").toLowerCase();
    case "band":
      // 2,4 vor 5 vor 6 GHz; Geräte ohne Angabe ans Ende.
      return { "2.4": 0, "5": 1, "6": 2 }[host.band] ?? 3;
    case "connected_via":
      // Ohne Mesh-Angabe ans Ende sortieren (wie bei "ha_name").
      return host.connected_via ? `0${String(host.connected_via).toLowerCase()}` : "1";
    case "label":
    case "note": {
      // Ohne Eintrag ans Ende (wie bei "ha_name").
      const text = String(host[key] || "").toLowerCase();
      return text ? `0${text}` : "1";
    }
    case "ha_name":
      // Geraete ohne Home-Assistant-Zuordnung ans Ende sortieren.
      return host.ha_name ? `0${String(host.ha_name).toLowerCase()}` : "1";
    case "ip_type": {
      // fest zuerst, dann dynamisch, dann ohne IP/unbekannt.
      const order = { fixed: 0, dynamic: 1, none: 2 };
      return order[host.ip_class] ?? 3;
    }
    case "wan":
      return host.blocked ? 0 : 1;
    case "update":
      return host.update_available ? 0 : 1;
    case "speed":
      return Number(host.speed) || 0;
    case "model":
      return String(host.model || "").toLowerCase();
    case "type":
      return String(host.device_class_user || host.device_class || "").toLowerCase();
    case "last_seen": {
      // Groesserer Zeitstempel = kuerzlich online. Aufsteigend sortiert
      // stehen damit die am laengsten offline Geraete oben; ohne Wert ganz
      // unten. Negiert, damit "aufsteigend" = "zuletzt online zuerst".
      const ts = Date.parse(host.last_seen || "");
      return Number.isNaN(ts) ? Number.POSITIVE_INFINITY : -ts;
    }
    default:
      return "";
  }
}

/* ------------------------------------------------------------------ */
/* Gruppierung, CSV (Idee 18)                                          */
/* ------------------------------------------------------------------ */

const GROUP_MODES = ["state", "connection", "vendor", "band", "subnet", "label"];

/** Dritter-Oktett-Bereich einer IPv4-Adresse ("192.168.2.x") oder "". */
function subnetOf(ip) {
  const m = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.\d{1,3}$/.exec(String(ip || "").trim());
  return m ? `${m[1]}.${m[2]}.${m[3]}.x` : "";
}

/**
 * Gruppenschlüssel eines Geräts. Rückgabe: { key, empty } - "empty" markiert
 * die Sammelgruppe "ohne Angabe", die ans Ende sortiert wird.
 */
function groupKeyOf(host, mode) {
  switch (mode) {
    case "state":
      return { key: host.active ? "1" : "0", empty: false };
    case "connection": {
      const kind = ["lan", "wlan", "powerline"].includes(host.connection) ? host.connection : "";
      return { key: kind, empty: !kind };
    }
    case "vendor": {
      const v = String(host.vendor || "").trim();
      return { key: v, empty: !v };
    }
    case "band": {
      const b = ["2.4", "5", "6"].includes(host.band) ? host.band : "";
      return { key: b, empty: !b };
    }
    case "subnet": {
      const n = subnetOf(host.ip);
      return { key: n, empty: !n };
    }
    case "label": {
      const l = String(host.label || "").trim();
      return { key: l, empty: !l };
    }
    default:
      return { key: "", empty: true };
  }
}

/**
 * Schützt einen CSV-Wert vor Formel-Einschleusung in Tabellenkalkulationen
 * (Werte, die mit = + - @ oder Tab/CR beginnen, bekommen ein ' vorangestellt)
 * und setzt ihn bei Bedarf in Anführungszeichen.
 */
function csvCell(value, delimiter) {
  let text = value === null || value === undefined ? "" : String(value);
  if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`;
  if (text.includes(delimiter) || /["\n\r]/.test(text)) {
    text = `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

/** Baut eine CSV-Datei (mit BOM für Excel) aus Kopfzeile und Datenzeilen. */
function buildCsv(header, rows, delimiter) {
  const lines = [header, ...rows].map((row) => row.map((cell) => csvCell(cell, delimiter)).join(delimiter));
  return `\ufeff${lines.join("\r\n")}\r\n`;
}

/* ------------------------------------------------------------------ */
/* Karte                                                               */
/* ------------------------------------------------------------------ */

class FritzboxNetzwerkCard extends HTMLElement {
  constructor() {
    super();
    this._config = withDefaults({});
    this._hass = null;
    this._search = "";
    this._filter = "alle";
    this._scopeCache = null;
    this._tab = "network";
    // Ob der Leerzustands-Hinweis inhaltlich faellig waere. Getrennt vom
    // hidden-Attribut gefuehrt, damit der Tab-Wechsel ihn korrekt wieder
    // einblenden kann, ohne die Tabelle neu zu zeichnen.
    this._emptyWanted = false;
    this._hasControls = false;
    this._sortBy = "ip";
    this._sortDir = "asc";
    this._signature = "";
    this._built = false;
    this._renderedOnce = false;
    this._lastStateObj = null;
    this._resizeObserver = null;
    // Popup: der Overlay-Knoten haengt am document.body, nicht in der
    // Karte - so liegt er sicher ueber allem, unabhaengig von den
    // Stapelkontexten des Dashboards. Gemerkt wird die MAC-Adresse des
    // gerade gezeigten Geraets, um den Inhalt bei neuen Sensordaten
    // aktualisieren zu koennen.
    this._popup = null;
    this._popupMac = null;
    this._popupReturnFocus = null;
    this._onPopupKeydown = null;
    // Umbenennen im Popup: waehrend der Bearbeitung wird das Popup nicht
    // neu aufgebaut (siehe _refreshPopup()), sonst ginge die Eingabe bei
    // jedem Hintergrund-Update (Polling) verloren.
    this._popupEditingName = false;
    this._popupNameDraft = "";
    // Bearbeiten von Etikett/Notiz im Popup (Idee 3), gleiches Prinzip.
    this._popupEditingNote = false;
    this._popupNoteDraft = null;
    // Gruppierung (Idee 18): aktueller Modus und eingeklappte Gruppen.
    this._groupBy = "";
    this._collapsed = new Set();
  }

  /* -- Lovelace-Schnittstelle -------------------------------------- */

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Bitte den Sensor mit der Geräteliste auswählen (entity).");
    }
    this._config = withDefaults(config);
    this._sortBy = this._config.sort_by;
    this._sortDir = this._config.sort_dir === "desc" ? "desc" : "asc";
    // Beim Laden/Neuöffnen mit dem konfigurierten Standardfilter starten.
    const wanted = this._config.default_filter;
    this._filter = FILTERS.some((f) => f.key === wanted) ? wanted : "alle";
    this._groupBy = GROUP_MODES.includes(this._config.group_by) ? this._config.group_by : "";
    this._collapsed = new Set();
    this._loadView();
    this._built = false;
    this._signature = "";
    this._renderedOnce = false;
    this._lastStateObj = null;
    this._closePopup();
    this._closeGastWlanPopup();
    this.innerHTML = "";
    if (this._hass) this._update();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  getCardSize() {
    const rows = this._hosts().length;
    return Math.min(12, 3 + Math.ceil(rows / 3));
  }

  /** Aktuelle Sprache (Konfig-Override oder HA-Einstellung). */
  _lang() {
    return resolveLang(this._config, this._hass);
  }

  /** Übersetzt einen Schlüssel in der aktuellen Sprache. */
  _t(key, params) {
    return translate(this._lang(), key, params);
  }

  /** Lokalisierte Verbindungsbezeichnung aus Art, Port und Gastflag. */
  _connLabel(host) {
    const kind = host.connection;
    let base;
    if (kind === "lan") base = host.port ? `LAN ${host.port}` : "LAN";
    else if (kind === "wlan") base = "WLAN";
    else if (kind === "powerline") base = "Powerline";
    else base = "—";
    if (host.guest) {
      const g = this._t("badge.guest");
      return base === "—" ? g : `${base} (${g})`;
    }
    return base;
  }

  /** Restlaufzeit der DHCP-Lease grob in Tagen (fuer die kompakte Anzeige). */
  _leaseDays(seconds) {
    const value = Number(seconds);
    if (!Number.isFinite(value) || value <= 0) return 0;
    return Math.max(1, Math.round(value / 86400));
  }

  static getConfigElement() {
    return document.createElement("fritzbox-netzwerk-card-editor");
  }

  static getStubConfig(hass) {
    // Den Sammelsensor erkennt man am Attribut "hosts" (eine Liste) - nicht am
    // Namen: die entity_id hängt von der Sprache ab (…_gerate, …_devices,
    // …_apparaten). Der Namenstreffer bleibt als Rückfall.
    const states = hass && hass.states ? hass.states : {};
    const ids = Object.keys(states).filter((id) => id.startsWith("sensor."));
    const entity =
      ids.find((id) => Array.isArray(states[id].attributes && states[id].attributes.hosts)) ||
      ids.find((id) => /gerate|devices|apparaten/.test(id));
    return { type: "custom:fritzbox-netzwerk-card", entity: entity || "" };
  }

  connectedCallback() {
    this._observeWidth();
  }

  disconnectedCallback() {
    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
      this._resizeObserver = null;
    }
    // Ein offenes Popup nicht verwaist am body haengen lassen.
    this._closePopup();
    this._closeGastWlanPopup();
  }

  /* -- Daten -------------------------------------------------------- */

  /* -- Gemerkte Ansicht (Idee 18) ---------------------------------- */

  /** Schlüssel im localStorage: je Sensor und IP-Filter eine eigene Ansicht. */
  _viewKey() {
    const spec = this._config.ip_filter;
    const filter = Array.isArray(spec) ? spec.join(",") : String(spec ?? "");
    return `fbn-view:${this._config.entity}:${filter}`;
  }

  /** Die Konfigurationswerte, aus denen die Startansicht entsteht. */
  _viewSignature() {
    const c = this._config;
    return [c.default_filter, c.sort_by, c.sort_dir, c.group_by].join("|");
  }

  /**
   * Übernimmt die gemerkte Ansicht - aber nur, solange sich die
   * Startwerte der Konfiguration seitdem nicht geändert haben; sonst würde
   * eine im Editor geänderte Vorgabe dauerhaft von einem alten Browserstand
   * überdeckt. Jeder Wert wird geprüft; localStorage kann fehlen oder
   * gesperrt sein.
   */
  _loadView() {
    if (!this._config.remember_view) return;
    let saved = null;
    try {
      saved = JSON.parse(window.localStorage.getItem(this._viewKey()) || "null");
    } catch (err) {
      saved = null;
    }
    if (!saved || typeof saved !== "object" || saved.sig !== this._viewSignature()) return;
    if (FILTERS.some((f) => f.key === saved.filter)) this._filter = saved.filter;
    if (COLUMNS.some((c) => c.key === saved.sortBy)) this._sortBy = saved.sortBy;
    if (saved.sortDir === "asc" || saved.sortDir === "desc") this._sortDir = saved.sortDir;
    if (saved.groupBy === "" || GROUP_MODES.includes(saved.groupBy)) this._groupBy = saved.groupBy;
    if (Array.isArray(saved.collapsed)) {
      this._collapsed = new Set(saved.collapsed.filter((k) => typeof k === "string").slice(0, 200));
    }
  }

  _saveView() {
    if (!this._config.remember_view) return;
    try {
      window.localStorage.setItem(
        this._viewKey(),
        JSON.stringify({
          sig: this._viewSignature(),
          filter: this._filter,
          sortBy: this._sortBy,
          sortDir: this._sortDir,
          groupBy: this._groupBy,
          collapsed: Array.from(this._collapsed),
        })
      );
    } catch (err) {
      /* localStorage nicht verfügbar - die Ansicht wird dann nur nicht gemerkt */
    }
  }

  _stateObj() {
    if (!this._hass || !this._config.entity) return null;
    return this._hass.states[this._config.entity] || null;
  }

  /** Alle Geräte des Sensors, unabhängig vom IP-Filter dieser Karte. */
  _allHosts() {
    const state = this._stateObj();
    if (!state || !state.attributes) return [];
    const hosts = state.attributes.hosts;
    return Array.isArray(hosts) ? hosts : [];
  }

  /**
   * Die Geräte im Geltungsbereich dieser Karte: alle, oder - bei gesetztem
   * ``ip_filter`` - nur die mit passender IP-Adresse. Filterleiste, Suche,
   * Zusammenfassung und Popup arbeiten alle auf dieser Auswahl. Das Ergebnis
   * wird je Sensorzustand und Filtertext zwischengespeichert, weil die Karte
   * es pro Aktualisierung mehrfach abfragt.
   */
  _hosts() {
    const all = this._allHosts();
    const spec = this._config.ip_filter;
    const key = Array.isArray(spec) ? spec.join(",") : String(spec ?? "");
    const cache = this._scopeCache;
    if (cache && cache.source === all && cache.key === key) return cache.hosts;

    const filter = parseIpFilter(spec);
    const hosts = filter ? all.filter((host) => ipMatchesFilter(host.ip, filter)) : all;
    this._scopeCache = { source: all, key, hosts };
    return hosts;
  }

  /** Erkennt, ob sich an den angezeigten Daten ueberhaupt etwas geaendert hat. */
  _computeSignature(hosts) {
    return hosts
      .map((host) =>
        [
          host.mac,
          host.ip,
          host.vendor,
          host.name,
          host.active ? 1 : 0,
          host.connection_label,
          host.band,
          host.connected_via,
          host.link_mbit,
          host.ha_name,
          host.static_ip,
          host.blocked ? 1 : 0,
          host.update_available ? 1 : 0,
          host.speed,
          host.label,
          host.note,
          host.reserved ? 1 : 0,
          host.ip_class,
        ].join("|")
      )
      .join("~");
  }

  /** Beschriftung des Funkbands ("2,4 GHz" ...) oder leer, wenn unbekannt. */
  _bandLabel(host) {
    const key = { "2.4": "band.24", "5": "band.5", "6": "band.6" }[host && host.band];
    return key ? this._t(key) : "";
  }

  _visibleColumns() {
    return COLUMNS.filter((column) => this._config[column.cfg]);
  }

  _filteredHosts(options) {
    const search = this._search.trim().toLowerCase();
    let hosts = this._hosts();

    if (this._config.hide_inactive) {
      hosts = hosts.filter((host) => host.active);
    }

    switch (this._filter) {
      case "aktiv":
        hosts = hosts.filter((host) => host.active);
        break;
      case "inaktiv":
        hosts = hosts.filter((host) => !host.active);
        break;
      case "gast":
        hosts = hosts.filter((host) => host.guest);
        break;
      case "gesperrt":
        hosts = hosts.filter((host) => host.blocked);
        break;
      case "update":
        hosts = hosts.filter((host) => host.update_available);
        break;
      case "fest":
        // Fest = am Gerät eingestellt oder von der Box reserviert (siehe
        // ip_class in hosts.py); aktive und inaktive Geräte.
        hosts = hosts.filter((host) => host.ip_class === "fixed");
        break;
      case "lange_offline": {
        // "last_seen" kommt vom Coordinator (hosts.apply_last_seen) und ist
        // für JEDES je gesehene Gerät gesetzt (anders als "first_seen" bei
        // "neu" oben) - fehlt es trotzdem, wurde das Gerät noch nie als
        // aktiv erfasst, zählt hier also ebenfalls als "lange offline".
        const threshold = Date.now() - LONG_OFFLINE_FILTER_DAYS * 24 * 60 * 60 * 1000;
        hosts = hosts.filter((host) => {
          if (host.active) return false;
          const ts = Date.parse(host.last_seen || "");
          return Number.isNaN(ts) || ts < threshold;
        });
        break;
      }
      case "neu": {
        // "first_seen" kommt vom Coordinator (hosts.apply_first_seen) und
        // ist nur gesetzt, wenn das Gerät seit der Einführung in 1.6.3
        // tatsächlich neu aufgetaucht ist - siehe dortigen Kommentar, warum
        // länger bekannte Geräte hier absichtlich KEINEN Wert haben (sie
        // sollen nach einem Update nicht plötzlich als "neu" erscheinen).
        const threshold = Date.now() - NEW_DEVICE_FILTER_DAYS * 24 * 60 * 60 * 1000;
        hosts = hosts.filter((host) => {
          const ts = Date.parse(host.first_seen || "");
          return !Number.isNaN(ts) && ts >= threshold;
        });
        break;
      }
      default:
        break;
    }

    if (search) {
      // Enthält die Eingabe "*" oder "?", gilt sie als Muster mit
      // Platzhaltern (z. B. "192.168.2.*" oder "drucker*"); sonst wie bisher
      // als einfacher Textausschnitt.
      const wildcard = /[*?]/.test(search) ? wildcardToRegExp(search, false) : null;
      hosts = hosts.filter((host) =>
        [host.name, host.ip, host.mac, host.vendor, this._bandLabel(host), host.ha_name, host.model, host.host_name, host.label, host.note]
          .map((value) => String(value || "").toLowerCase())
          .some((value) => (wildcard ? wildcard.test(value) : value.includes(search)))
      );
    }

    const direction = this._sortDir === "desc" ? -1 : 1;
    const sorted = hosts.slice().sort((left, right) => {
      const a = sortValue(left, this._sortBy);
      const b = sortValue(right, this._sortBy);
      if (a < b) return -1 * direction;
      if (a > b) return 1 * direction;
      // Stabiler Zweitschluessel, damit die Reihenfolge nicht springt.
      return ipSortKey(left.ip) - ipSortKey(right.ip);
    });

    const limit = Number(this._config.max_rows) || 0;
    if (options && options.ignoreLimit) return sorted;
    return limit > 0 ? sorted.slice(0, limit) : sorted;
  }

  /* -- Aufbau ------------------------------------------------------- */

  _update() {
    if (!this._hass) return;
    if (!this._built) {
      this._build();
      this._built = true;
    }

    // Home Assistant ruft den hass-Setter bei JEDER Zustandsaenderung im
    // ganzen System auf - viele Male pro Sekunde. Ohne Bremse wuerde die
    // Karte den kompletten Tabellenkoerper jedes Mal neu aufbauen; bei
    // vielen Geraeten (z. B. 160 Zeilen mit je mehreren <ha-icon>) treibt
    // das CPU und Speicher massiv nach oben und laesst den Browser
    // einfrieren.
    //
    // Zwei gestaffelte Bremsen:
    // 1) Solange das Zustandsobjekt des Sensors dieselbe Referenz hat, kann
    //    sich nichts geaendert haben - dann sofort abbrechen (O(1)).
    // 2) Aendert sich die Referenz, entscheidet die inhaltliche Signatur,
    //    ob wirklich neu gezeichnet werden muss.
    const stateObj = this._stateObj();
    if (this._renderedOnce && stateObj === this._lastStateObj) {
      return;
    }
    this._lastStateObj = stateObj;

    // Die Steuerungsleiste (WLAN-Status, Down/Up) ist guenstig und aendert
    // sich unabhaengig von der Geraeteliste - daher bei jedem neuen
    // Zustandsobjekt aktualisieren, ohne die teure Tabelle anzufassen.
    this._renderControls();
    this._renderTabs();

    const hosts = this._hosts();
    const signature = this._computeSignature(hosts);
    if (this._renderedOnce && signature === this._signature) {
      // Referenz war neu, Inhalt aber gleich - Popup ggf. auffrischen,
      // aber die Tabelle unangetastet lassen.
      if (this._popup) this._refreshPopup();
      return;
    }
    this._signature = signature;
    this._renderedOnce = true;

    this._renderSummary();
    this._renderBody();
    if (this._popup) this._refreshPopup();
  }

  _build() {
    const config = this._config;
    this.innerHTML = "";

    const card = document.createElement("ha-card");
    card.className = "fbn-card";
    if (config.show_title && config.title) {
      card.setAttribute("header", config.title);
    }
    card.innerHTML = `
      <style>${this._styles()}</style>
      <div class="fbn-root${config.compact ? " fbn-compact" : ""}${
      config.sticky_name ? " fbn-sticky" : ""
    }">
        <div class="fbn-tabbar" role="tablist" hidden></div>
        <div class="fbn-toolbar" data-tab="network">
          <div class="fbn-filters"></div>
          <div class="fbn-searchwrap"></div>
          <div class="fbn-copywrap"></div>
          <div class="fbn-tools"></div>
        </div>
        <div class="fbn-summary" data-tab="network"></div>
        <div class="fbn-controls" data-tab="controls" hidden></div>
        <div class="fbn-scrollwrap" data-tab="network">
          <button class="fbn-arrow fbn-arrow-left" type="button" hidden
                  aria-label="${escapeHtml(this._t('arrow.left'))}" tabindex="-1">
            <ha-icon icon="mdi:chevron-left"></ha-icon>
          </button>
          <div class="fbn-scroll">
            <table class="fbn-table">
              <thead><tr class="fbn-head"></tr></thead>
              <tbody class="fbn-body"></tbody>
            </table>
          </div>
          <button class="fbn-arrow fbn-arrow-right" type="button" hidden
                  aria-label="${escapeHtml(this._t('arrow.right'))}" tabindex="-1">
            <ha-icon icon="mdi:chevron-right"></ha-icon>
          </button>
        </div>
        <div class="fbn-empty" data-tab="network" hidden></div>
      </div>
    `;
    this.appendChild(card);

    this._root = card.querySelector(".fbn-root");
    this._root.style.cssText = this._colorVars();

    this._buildFilters();
    this._buildSearch();
    this._buildCopyButton();
    this._buildTools();
    this._buildHead();
    this._renderHead();
    this._renderControls();
    this._renderTabs();
    this._observeWidth();
    this._bindScrollArrows(card.querySelector(".fbn-scrollwrap"));
  }

  /** Liste der aktuell eingeschalteten Filter-Buttons. */
  _visibleFilters() {
    return FILTERS.filter((filter) => this._config[`filter_${filter.key}`] !== false);
  }

  _buildFilters() {
    const container = this.querySelector(".fbn-filters");
    if (!container) return;
    const filters = this._visibleFilters();
    if (!this._config.show_filter || filters.length === 0) {
      container.hidden = true;
      return;
    }
    container.hidden = false;

    // Ist der aktive Filter ausgeblendet, auf den ersten sichtbaren
    // zurückfallen (bevorzugt "Alle"), damit nicht heimlich nach einer
    // unsichtbaren Kategorie gefiltert wird.
    if (!filters.some((filter) => filter.key === this._filter)) {
      const fallback = filters.some((f) => f.key === "alle")
        ? "alle"
        : filters[0].key;
      this._filter = fallback;
    }

    container.innerHTML = filters
      .map(
        (filter) => `
        <button class="fbn-chip" data-filter="${filter.key}" type="button"
                aria-pressed="${filter.key === this._filter}">
          <ha-icon class="fbn-chip-icon" icon="${filter.icon}" style="color:var(--fbn-cat-${filter.key})"></ha-icon><span>${escapeHtml(this._t(`flt.${filter.key}`))}</span>
        </button>`
      )
      .join("");
    container.addEventListener("click", (event) => {
      const button = event.target.closest(".fbn-chip");
      if (!button) return;
      this._setFilter(button.dataset.filter);
    });
  }

  /* -- Waagerechtes Blättern (Smartphone) --------------------------- */

  /**
   * Auf schmalen Karten passen nicht alle Spalten nebeneinander. Statt
   * Spalten zu verstecken, wird die Tabelle waagerecht scrollbar: per
   * Wischgeste (nativer Touch-Scroll) oder ueber die beiden Pfeile am
   * Rand. Der Gerätename bleibt dabei links stehen (siehe fbn-sticky).
   */
  _bindScrollArrows(wrapEl) {
    if (!wrapEl || wrapEl.dataset.arrowsBound) return;
    wrapEl.dataset.arrowsBound = "1";
    const scrollEl = wrapEl.querySelector(".fbn-scroll");
    const left = wrapEl.querySelector(".fbn-arrow-left");
    const right = wrapEl.querySelector(".fbn-arrow-right");
    if (!scrollEl) return;
    this._scrollEl = scrollEl;

    const step = () => Math.max(120, Math.round(scrollEl.clientWidth * 0.66));
    if (left) {
      left.addEventListener("click", () => {
        scrollEl.scrollBy({ left: -step(), behavior: "smooth" });
      });
    }
    if (right) {
      right.addEventListener("click", () => {
        scrollEl.scrollBy({ left: step(), behavior: "smooth" });
      });
    }
    scrollEl.addEventListener("scroll", () => this._updateArrows(), {
      passive: true,
    });
    this._updateArrows();
  }

  /**
   * Blendet die Pfeile passend zur Scrollposition ein oder aus: linker
   * Pfeil nur, wenn nach links scrollbar; rechter nur, wenn nach rechts.
   * Ist die Tabelle komplett sichtbar, bleiben beide verborgen.
   */
  _updateArrows() {
    const scrollEl = this._scrollEl;
    if (!scrollEl) return;
    const wrap = scrollEl.closest(".fbn-scrollwrap");
    if (!wrap) return;
    const left = wrap.querySelector(".fbn-arrow-left");
    const right = wrap.querySelector(".fbn-arrow-right");
    const arrowsOn = this._config.show_scroll_arrows;
    const maxScroll = scrollEl.scrollWidth - scrollEl.clientWidth;
    const pos = scrollEl.scrollLeft;
    // 2px Toleranz gegen Rundungsfehler.
    const canLeft = arrowsOn && pos > 2;
    const canRight = arrowsOn && pos < maxScroll - 2;
    if (left) {
      left.hidden = !canLeft;
      left.tabIndex = canLeft ? 0 : -1;
    }
    if (right) {
      right.hidden = !canRight;
      right.tabIndex = canRight ? 0 : -1;
    }
  }

  /** Setzt den aktiven Filter und aktualisiert Chips, Zusammenfassung, Liste. */
  _setFilter(key) {
    if (!FILTERS.some((filter) => filter.key === key)) return;
    if (key === this._filter) return;
    this._filter = key;
    this.querySelectorAll(".fbn-chip").forEach((chip) => {
      chip.setAttribute("aria-pressed", String(chip.dataset.filter === key));
    });
    this._buildCopyButton();
    this._renderSummary();
    this._renderBody();
    this._saveView();
  }

  /**
   * Knopf "Namen/MAC-Adressen kopieren" - nur sichtbar beim Filter
   * "Lange offline" (Idee 6 aus feature-ideen.md): Arbeitsgrundlage, um
   * lange nicht mehr gesehene Geräte in der FRITZ!Box aufzuräumen.
   */
  _buildCopyButton() {
    const container = this.querySelector(".fbn-copywrap");
    if (!container) return;
    if (this._filter !== "lange_offline") {
      container.hidden = true;
      container.innerHTML = "";
      return;
    }
    container.hidden = false;
    container.innerHTML = `
      <button class="fbn-copy-list" type="button">
        <ha-icon icon="mdi:content-copy"></ha-icon>
        <span>${escapeHtml(this._t("btn.copy_list"))}</span>
      </button>`;
    const button = container.querySelector(".fbn-copy-list");
    button.addEventListener("click", async () => {
      const lines = this._filteredHosts().map((host) => `${host.name}\t${host.mac}`);
      const ok = await copyToClipboard(lines.join("\n"), this);
      button.classList.remove("fbn-copy-ok", "fbn-copy-fail");
      button.classList.add(ok ? "fbn-copy-ok" : "fbn-copy-fail");
      setTimeout(() => button.classList.remove("fbn-copy-ok", "fbn-copy-fail"), 2000);
    });
  }

  /** Gruppierungs-Auswahl und CSV-Knopf in der Werkzeugleiste (Idee 18). */
  _buildTools() {
    const container = this.querySelector(".fbn-tools");
    if (!container) return;
    const showGroup = this._config.show_group_select !== false;
    const showCsv = this._config.show_csv_export !== false;
    if (!showGroup && !showCsv) {
      container.hidden = true;
      return;
    }
    container.hidden = false;
    const options = ["", ...GROUP_MODES]
      .map(
        (mode) =>
          `<option value="${mode}"${mode === this._groupBy ? " selected" : ""}>${escapeHtml(
            this._t(mode ? `group.${mode}` : "group.none")
          )}</option>`
      )
      .join("");
    container.innerHTML = `
      ${
        showGroup
          ? `<label class="fbn-group-select">
               <ha-icon icon="mdi:format-list-group"></ha-icon>
               <select aria-label="${escapeHtml(this._t("group.aria"))}">${options}</select>
             </label>`
          : ""
      }
      ${
        showCsv
          ? `<button class="fbn-copy-list fbn-csv" type="button" title="${escapeHtml(this._t("btn.csv_tip"))}">
               <ha-icon icon="mdi:file-delimited-outline"></ha-icon>
               <span>${escapeHtml(this._t("btn.csv"))}</span>
             </button>`
          : ""
      }`;
    const select = container.querySelector("select");
    if (select) {
      select.addEventListener("change", () => this._setGroup(select.value));
    }
    const csv = container.querySelector(".fbn-csv");
    if (csv) csv.addEventListener("click", () => this._exportCsv(csv));
  }

  _setGroup(mode) {
    const next = GROUP_MODES.includes(mode) ? mode : "";
    if (next === this._groupBy) return;
    this._groupBy = next;
    this._renderBody();
    this._saveView();
  }

  /** Beschriftung einer Gruppe; leere Sammelgruppe = "ohne Angabe". */
  _groupLabel(mode, group) {
    switch (mode) {
      case "state":
        return this._t(group.key === "1" ? "flt.aktiv" : "flt.inaktiv");
      case "connection":
        return group.empty
          ? this._t("group.empty.connection")
          : { lan: "LAN", wlan: "WLAN", powerline: "Powerline" }[group.key];
      case "band":
        return group.empty
          ? this._t("group.empty.band")
          : this._t({ "2.4": "band.24", "5": "band.5", "6": "band.6" }[group.key]);
      case "vendor":
        return group.empty ? this._t("group.empty.vendor") : group.key;
      case "subnet":
        return group.empty ? this._t("group.empty.subnet") : group.key;
      case "label":
        return group.empty ? this._t("group.empty.label") : group.key;
      default:
        return group.key;
    }
  }

  /** Teilt die (bereits sortierten) Geräte in Gruppen; Reihenfolge innerhalb bleibt. */
  _groupHosts(hosts) {
    const mode = this._groupBy;
    const groups = new Map();
    hosts.forEach((host) => {
      const info = groupKeyOf(host, mode);
      const id = `${mode}:${info.key}`;
      if (!groups.has(id)) groups.set(id, { id, key: info.key, empty: info.empty, hosts: [] });
      groups.get(id).hosts.push(host);
    });
    const list = Array.from(groups.values());
    list.sort((a, b) => {
      if (a.empty !== b.empty) return a.empty ? 1 : -1;
      if (mode === "state") return a.key < b.key ? 1 : -1; // aktiv zuerst
      if (mode === "subnet") return ipSortKey(a.key.replace(/x$/, "0")) - ipSortKey(b.key.replace(/x$/, "0"));
      if (mode === "band") return ({ "2.4": 0, "5": 1, "6": 2 }[a.key] ?? 3) - ({ "2.4": 0, "5": 1, "6": 2 }[b.key] ?? 3);
      return String(this._groupLabel(mode, a)).localeCompare(String(this._groupLabel(mode, b)), this._lang());
    });
    return list;
  }

  /* -- CSV-Export (Idee 18) ------------------------------------------ */

  /** Ein Zellwert für die CSV-Datei (Klartext, ohne HTML). */
  _csvValue(host, key) {
    switch (key) {
      case "status":
        return this._t(host.active ? "state.connected" : "state.disconnected");
      case "connection":
        return this._connLabel(host);
      case "band":
        return this._bandLabel(host);
      case "connected_via":
        return host.connected_via || "";
      case "ip_type":
        return host.ip_class === "fixed"
          ? this._t("iptype.fixed")
          : host.ip_class === "dynamic"
          ? this._t("iptype.dynamic")
          : host.ip_class === "none"
          ? this._t("iptype.noip")
          : "";
      case "wan":
        return this._t(host.blocked ? "wan.blocked" : "wan.allowed");
      case "update":
        return this._t(host.update_available ? "upd.available" : "upd.none");
      case "speed":
        return host.active && host.speed ? host.speed : "";
      case "type":
        return host.device_class_user || host.device_class || "";
      case "vendor":
        return host.vendor || (host.mac_random ? this._t("vendor.random") : "");
      default:
        return host[key] === undefined || host[key] === null ? "" : host[key];
    }
  }

  /** Baut den CSV-Text der aktuell gefilterten Liste (alle Treffer, ohne Zeilenlimit). */
  _buildCsvText() {
    const columns = this._visibleColumns();
    const header = columns.map((column) => this._t(`col.${column.key}`));
    const rows = this._filteredHosts({ ignoreLimit: true }).map((host) =>
      columns.map((column) => this._csvValue(host, column.key))
    );
    // In Deutschland/den Niederlanden erwartet Excel ";" als Trenner.
    const delimiter = ["de", "nl"].includes(this._lang()) ? ";" : ",";
    return buildCsv(header, rows, delimiter);
  }

  async _exportCsv(button) {
    const text = this._buildCsvText();
    let ok = false;
    try {
      const blob = new Blob([text], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `netzwerkgeraete-${new Date().toISOString().slice(0, 10)}.csv`;
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
      ok = true;
    } catch (err) {
      ok = false;
    }
    if (!ok) {
      // Manche Umgebungen (z. B. eingebettete Ansichten) blockieren Downloads:
      // dann landet der Text wenigstens in der Zwischenablage.
      ok = await copyToClipboard(text, this);
      this.dispatchEvent(
        new CustomEvent("hass-notification", {
          detail: { message: this._t(ok ? "csv.copied" : "csv.failed") },
          bubbles: true,
          composed: true,
        })
      );
    }
    if (button) {
      button.classList.remove("fbn-copy-ok", "fbn-copy-fail");
      button.classList.add(ok ? "fbn-copy-ok" : "fbn-copy-fail");
      setTimeout(() => button.classList.remove("fbn-copy-ok", "fbn-copy-fail"), 2000);
    }
  }

  _buildSearch() {
    const container = this.querySelector(".fbn-searchwrap");
    if (!container) return;
    if (!this._config.show_search) {
      container.hidden = true;
      return;
    }
    container.innerHTML = `
      <label class="fbn-search">
        <ha-icon icon="mdi:magnify"></ha-icon>
        <input type="search" placeholder="${escapeHtml(this._t('search.placeholder'))}" aria-label="${escapeHtml(this._t('search.aria'))}">
      </label>`;
    const input = container.querySelector("input");
    input.addEventListener("input", () => {
      this._search = input.value;
      this._renderSummary();
      this._renderBody();
    });
  }

  /**
   * Baut den Tabellenkopf genau einmal. Beim Sortieren wird danach nur
   * noch der Zustand der vorhandenen Zellen umgeschaltet - wuerde hier
   * innerHTML neu gesetzt, verloere ein gerade angeklicktes <th> mitten
   * im Klick seinen Platz im Dokument und der Tastaturfokus spraenge.
   */
  _buildHead() {
    const row = this.querySelector(".fbn-head");
    if (!row) return;
    row.innerHTML = this._visibleColumns()
      .map((column) => {
        const header = this._t(`col.${column.key}`);
        // Statusspalte zeigt kein Textlabel, aber Tooltip/aria "Status".
        const cellLabel = column.key === "status" ? "" : header;
        return `
          <th class="fbn-th fbn-col-${column.key} fbn-prio-${column.prio}"
              data-sort="${column.key}" scope="col" tabindex="0" role="columnheader"
              style="text-align:${column.align || "left"}"
              title="${escapeHtml(this._t("tip.sort", { label: header }))}">
            <span class="fbn-th-inner">
              <span class="fbn-th-label">${escapeHtml(cellLabel)}</span>
              <ha-icon class="fbn-sorticon" icon="mdi:arrow-up" hidden></ha-icon>
            </span>
          </th>`;
      })
      .join("");

    const sort = (key) => {
      if (this._sortBy === key) {
        this._sortDir = this._sortDir === "asc" ? "desc" : "asc";
      } else {
        this._sortBy = key;
        this._sortDir = "asc";
      }
      this._renderHead();
      this._renderBody();
      this._saveView();
    };

    row.addEventListener("click", (event) => {
      const header = event.target.closest("th[data-sort]");
      if (header) sort(header.dataset.sort);
    });
    row.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      const header = event.target.closest("th[data-sort]");
      if (!header) return;
      event.preventDefault();
      sort(header.dataset.sort);
    });
  }

  /** Schaltet Markierung und Sortierpfeil auf die aktive Spalte um. */
  _renderHead() {
    const row = this.querySelector(".fbn-head");
    if (!row) return;
    if (!row.children.length) this._buildHead();

    row.querySelectorAll("th[data-sort]").forEach((header) => {
      const active = header.dataset.sort === this._sortBy;
      header.classList.toggle("fbn-sorted", active);
      header.setAttribute(
        "aria-sort",
        active ? (this._sortDir === "asc" ? "ascending" : "descending") : "none"
      );
      const icon = header.querySelector(".fbn-sorticon");
      if (!icon) return;
      icon.hidden = !active;
      if (active) {
        icon.setAttribute(
          "icon",
          this._sortDir === "asc" ? "mdi:arrow-up" : "mdi:arrow-down"
        );
      }
    });
  }

  _renderSummary() {
    const container = this.querySelector(".fbn-summary");
    if (!container) return;
    if (!this._config.show_summary) {
      container.hidden = true;
      return;
    }
    const state = this._stateObj();
    let attributes = (state && state.attributes) || {};
    // Mit IP-Filter beziehen sich die Zahlen nur auf die Geräte dieser Karte,
    // nicht auf das ganze Netz - sie werden dann aus der Auswahl gezählt.
    if (parseIpFilter(this._config.ip_filter)) {
      const scoped = this._hosts();
      attributes = {
        gesamt: scoped.length,
        aktiv: scoped.filter((host) => host.active).length,
        updates_verfuegbar: scoped.filter((host) => host.update_available).length,
        gesperrt: scoped.filter((host) => host.blocked).length,
      };
    }
    const shown = this._filteredHosts().length;
    const parts = [
      this._t("sum.devices", { n: attributes.gesamt || 0 }),
      this._t("sum.active", { n: attributes.aktiv || 0 }),
    ];
    if (attributes.updates_verfuegbar) {
      parts.push(this._t("sum.updates", { n: attributes.updates_verfuegbar }));
    }
    if (attributes.gesperrt) {
      parts.push(this._t("sum.blocked", { n: attributes.gesperrt }));
    }
    const filtered =
      shown !== (attributes.gesamt || 0)
        ? ` · ${this._t("sum.shown", { n: shown })}`
        : "";
    container.textContent = parts.join(" · ") + filtered;
  }

  /* -- Steuerungsleiste (WLAN / Reconnect / Neustart / Down-Up) ------ */

  /**
   * Zeichnet die optionale Steuerungs-Kategorie: Live-Down/Up, WLAN-Schalter
   * und die Buttons Neuverbinden/Neustart. Die eigentlichen Aktionen laufen
   * ueber generische Dienstaufrufe an die vom Sensor gemeldeten Entitaeten,
   * die Karte selbst bleibt also datengetrieben.
   */
  /**
   * Installierte Version der Integration; bei einer neueren Version bei GitHub zusätzlich
   * ein farblich hervorgehobener Hinweis direkt daneben (Link zu den Release-Notizen). Weicht die
   * Version der Karte von der der Integration ab (alter Browser-Cache), erscheint ein Warnhinweis.
   */
  _versionHtml(info) {
    const t = (key, params) => escapeHtml(this._t(key, params));
    const chips = [
      `<span class="fbn-ctl-version" title="${t("ver.title")}"><ha-icon icon="mdi:tag-outline"></ha-icon>v${escapeHtml(
        String(info.installed)
      )}</span>`,
    ];
    if (info.update_available && info.latest) {
      const params = { version: String(info.latest) };
      const url =
        typeof info.release_url === "string" && info.release_url.startsWith("https://github.com/")
          ? info.release_url
          : "";
      const inner = `<ha-icon icon="mdi:arrow-up-bold-circle-outline"></ha-icon>${t("ver.update", params)}`;
      chips.push(
        url
          ? `<a class="fbn-ctl-update" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer"
                title="${t("ver.update_tip", params)}">${inner}</a>`
          : `<span class="fbn-ctl-update" title="${t("ver.update_plain_tip", params)}">${inner}</span>`
      );
    }
    if (String(info.installed) !== FBN_VERSION) {
      chips.push(
        `<span class="fbn-ctl-update fbn-ctl-mismatch"><ha-icon icon="mdi:alert-outline"></ha-icon>${t("ver.card_mismatch", {
          card: FBN_VERSION,
          integration: String(info.installed),
        })}</span>`
      );
    }
    return `<span class="fbn-ctl-verbox">${chips.join("")}</span>`;
  }

  _renderControls() {
    const box = this.querySelector(".fbn-controls");
    if (!box) return;
    const state = this._stateObj();
    const attributes = (state && state.attributes) || {};
    const connection = attributes.connection || null;
    const controls = attributes.controls || null;
    const mesh = attributes.mesh && Array.isArray(attributes.mesh.members) ? attributes.mesh : null;
    const version =
      this._config.show_version !== false && attributes.version && attributes.version.installed
        ? attributes.version
        : null;

    // Ohne Schalter (Einstellung aus) und ohne Verbindungsdaten: leeren.
    if (!this._config.show_controls || (!connection && !controls && !mesh && !version)) {
      box.innerHTML = "";
      this._hasControls = false;
      this._applyTabs();
      return;
    }
    this._hasControls = true;

    const parts = [];
    if (connection && (connection.down_rate != null || connection.up_rate != null)) {
      parts.push(`
        <span class="fbn-ctl-rate" title="${escapeHtml(this._t("ctl.throughput"))}">
          <ha-icon icon="mdi:download"></ha-icon>${escapeHtml(formatRate(connection.down_rate))}
          <ha-icon icon="mdi:upload"></ha-icon>${escapeHtml(formatRate(connection.up_rate))}
        </span>`);
    }
    if (controls && Array.isArray(controls.wlan)) {
      for (const w of controls.wlan) {
        const on = w.on === true;
        const pressed = w.on === false ? "false" : w.on === true ? "true" : "mixed";
        parts.push(`
          <button class="fbn-ctl-chip fbn-ctl-wlan" type="button"
                  data-entity="${escapeHtml(w.entity_id)}" aria-pressed="${pressed}">
            <ha-icon icon="${w.key === "wlan_guest" ? "mdi:wifi-lock" : on ? "mdi:wifi" : "mdi:wifi-off"}"></ha-icon>
            <span>${escapeHtml(this._t(`ctl.${w.key}`))}</span>
          </button>`);
      }
      // QR-Code-Knopf (Idee 11): nur, wenn ein Gast-WLAN-Schalter existiert -
      // dieselbe Bedingung, unter der der Dienst gast_wlan_info arbeitet
      // (siehe GAST_WLAN_SERVICE_INDEX in __init__.py).
      if (controls.wlan.some((w) => w.key === "wlan_guest")) {
        parts.push(`
          <button class="fbn-ctl-btn fbn-ctl-gastwlan-qr" type="button"
                  title="${escapeHtml(this._t("ctl.gast_wlan_qr_tip"))}">
            <ha-icon icon="mdi:qrcode"></ha-icon>
            <span>${escapeHtml(this._t("ctl.gast_wlan_qr"))}</span>
          </button>`);
      }
    }
    if (controls && controls.mac_filter) {
      const pairingEnds = controls.pairing_ends || null;
      const filterOn = controls.mac_filter_on === true;
      const pressed = pairingEnds ? "false" : controls.mac_filter_on === false ? "false" : filterOn ? "true" : "mixed";
      const label = pairingEnds
        ? this._t("ctl.pairing_until", { time: this._formatTime(pairingEnds) })
        : this._t("ctl.mac_filter");
      const tip = pairingEnds ? this._t("ctl.pairing_end_tip") : this._t("ctl.mac_filter_tip");
      parts.push(`
        <button class="fbn-ctl-chip fbn-ctl-mac${pairingEnds ? " fbn-ctl-armed" : ""}" type="button"
                data-entity="${escapeHtml(controls.mac_filter)}" aria-pressed="${pressed}"
                title="${escapeHtml(tip)}">
          <ha-icon icon="${filterOn ? "mdi:shield-lock" : pairingEnds ? "mdi:shield-key" : "mdi:shield-off"}"></ha-icon>
          <span>${escapeHtml(label)}</span>
        </button>`);
    }
    // Pairing nur anbieten, solange der Filter an ist und kein Pairing laeuft.
    if (controls && controls.pairing && controls.mac_filter_on === true && !controls.pairing_ends) {
      parts.push(`
        <button class="fbn-ctl-btn fbn-ctl-pairing" type="button" data-armed="0"
                data-entity="${escapeHtml(controls.pairing)}"
                title="${escapeHtml(this._t("ctl.pairing_tip"))}">
          <ha-icon icon="mdi:shield-key"></ha-icon><span>${escapeHtml(this._t("ctl.pairing"))}</span>
        </button>`);
    }
    if (controls && controls.reconnect) {
      parts.push(`
        <button class="fbn-ctl-btn fbn-ctl-reconnect" type="button" data-armed="0"
                data-entity="${escapeHtml(controls.reconnect)}">
          <ha-icon icon="mdi:restart"></ha-icon><span>${escapeHtml(this._t("ctl.reconnect"))}</span>
        </button>`);
    }
    if (controls && controls.reboot) {
      parts.push(`
        <button class="fbn-ctl-btn fbn-ctl-reboot" type="button"
                data-entity="${escapeHtml(controls.reboot)}" data-armed="0">
          <ha-icon icon="mdi:restart-alert"></ha-icon><span>${escapeHtml(this._t("ctl.reboot"))}</span>
        </button>`);
    }
    if (mesh) parts.push(this._renderMesh(mesh, controls));
    if (version) parts.push(this._versionHtml(version));
    box.innerHTML = parts.join("");

    if (!box.dataset.bound) {
      box.dataset.bound = "1";
      box.addEventListener("click", (event) => this._onControlClick(event));
    }
    this._applyTabs();
  }

  /**
   * Mesh-Gruppe: die FRITZ!Box und ihre Repeater als eine Einheit, mit
   * Online-Zaehler, den einzelnen Mitgliedern und - wenn die Steuerung
   * aktiv ist - dem Button "Alle neu starten".
   */
  _renderMesh(mesh, controls) {
    const members = mesh.members
      .map((m) => {
        const box = m.role === "box";
        const on = m.online !== false;
        const icon = box ? "mdi:router-wireless" : on ? "mdi:access-point-network" : "mdi:access-point-network-off";
        const tip = [m.model, m.ip].filter(Boolean).join(" \u00b7 ");
        return `
          <span class="fbn-mesh-member ${on ? "fbn-mesh-on" : "fbn-mesh-off"}"
                title="${escapeHtml(tip)}">
            <ha-icon icon="${icon}"></ha-icon><span>${escapeHtml(m.name || "")}</span>
          </span>`;
      })
      .join("");
    const rebootAll = mesh.reboot_all || (controls && controls.reboot_mesh) || null;
    const button = rebootAll
      ? `<button class="fbn-ctl-btn fbn-ctl-reboot-mesh" type="button"
                 data-entity="${escapeHtml(rebootAll)}" data-armed="0"
                 title="${escapeHtml(this._t("ctl.mesh_reboot_tip"))}">
           <ha-icon icon="mdi:router-network"></ha-icon><span>${escapeHtml(this._t("ctl.mesh_reboot"))}</span>
         </button>`
      : "";
    const complete = mesh.online === mesh.total;
    return `
      <div class="fbn-mesh${complete ? "" : " fbn-mesh-incomplete"}" role="group"
           aria-label="${escapeHtml(this._t("ctl.mesh"))}">
        <span class="fbn-mesh-title">
          <ha-icon icon="mdi:router-network"></ha-icon>
          <strong>${escapeHtml(this._t("ctl.mesh"))}</strong>
          <span>${escapeHtml(this._t("ctl.mesh_online", { online: mesh.online, total: mesh.total }))}</span>
        </span>
        <span class="fbn-mesh-members">${members}</span>
        ${button}
      </div>`;
  }

  /* -- Tabs (Kategorien) -------------------------------------------- */

  /** Welche Tabs es aktuell gibt: Netzwerk immer, Steuerung wenn vorhanden. */
  _tabList() {
    const tabs = [{ key: "network", icon: "mdi:lan" }];
    if (this._hasControls) {
      tabs.push({ key: "controls", icon: "mdi:router-wireless-settings" });
    }
    return tabs;
  }

  /** Baut die Tab-Leiste (einmalig verkabelt). */
  _renderTabs() {
    const bar = this.querySelector(".fbn-tabbar");
    if (!bar) return;
    const tabs = this._tabList();
    // Nur zeigen, wenn Tabs eingeschaltet UND mehr als eine Kategorie da ist.
    if (!this._config.show_tabs || tabs.length < 2) {
      bar.hidden = true;
      bar.innerHTML = "";
      this._applyTabs();
      return;
    }
    bar.hidden = false;
    if (!tabs.some((t) => t.key === this._tab)) this._tab = tabs[0].key;
    bar.innerHTML = tabs
      .map(
        (t) => `
        <button class="fbn-tab" type="button" role="tab" data-tab="${t.key}"
                aria-selected="${t.key === this._tab}">
          <ha-icon icon="${t.icon}"></ha-icon><span>${escapeHtml(this._t(`tab.${t.key}`))}</span>
        </button>`
      )
      .join("");
    if (!bar.dataset.bound) {
      bar.dataset.bound = "1";
      bar.addEventListener("click", (event) => {
        const button = event.target.closest(".fbn-tab");
        if (!button) return;
        this._tab = button.dataset.tab;
        this._renderTabs();
      });
    }
    this._applyTabs();
  }

  /**
   * Ist die Netzwerk-Kategorie gerade sichtbar? Ohne Tabs immer, mit Tabs
   * nur im Reiter "Netzwerk". Wird auch vom Leerzustand ausgewertet.
   */
  _networkVisible() {
    const tabs = this._tabList();
    if (!this._config.show_tabs || tabs.length < 2) return true;
    return this._tab === "network";
  }

  /**
   * Steuert die Sichtbarkeit der Sektionen anhand des aktiven Tabs.
   *
   * Sind die Kategorien als Tabs eingeschaltet, gehoert jede Sektion genau
   * EINER Kategorie: Netzwerk = Filterleiste, Suche, Zusammenfassung,
   * Tabelle, Leerhinweis; Steuerung = Down/Up, WLAN-Schalter,
   * Neuverbinden/Neustart. Es wird nichts doppelt gezeigt. Ohne Tabs
   * erscheinen wie bisher beide Bereiche untereinander.
   */
  _applyTabs() {
    const root = this._root;
    if (!root) return;
    const tabs = this._tabList();
    const tabbed = this._config.show_tabs && tabs.length > 1;
    const controls = root.querySelector(".fbn-controls");
    const empty = root.querySelector(".fbn-empty");

    // WICHTIG: nur die direkten Sektionen von .fbn-root, nicht die
    // Tab-Schaltflaechen in der Leiste - die tragen selbst ein data-tab.
    const sections = Array.from(root.children).filter((el) =>
      el.hasAttribute("data-tab")
    );

    if (!tabbed) {
      // Ohne Tabs: Netzwerk-Sektionen sichtbar, Steuerung nur bei Inhalt.
      sections.forEach((el) => {
        if (el.getAttribute("data-tab") !== "network") return;
        if (!el.classList.contains("fbn-empty")) el.hidden = false;
      });
      if (empty) empty.hidden = !this._emptyWanted;
      if (controls) controls.hidden = !this._hasControls;
      return;
    }
    // Mit Tabs: ausschliesslich die Sektionen des aktiven Tabs zeigen.
    if (!tabs.some((t) => t.key === this._tab)) this._tab = tabs[0].key;
    sections.forEach((el) => {
      const belongs = el.getAttribute("data-tab") === this._tab;
      // Der Leerhinweis erscheint nur, wenn er inhaltlich faellig ist.
      if (el.classList.contains("fbn-empty")) {
        el.hidden = !belongs || !this._emptyWanted;
        return;
      }
      el.hidden = !belongs;
    });
    if (controls && this._tab === "controls") controls.hidden = !this._hasControls;
  }

  /** Reagiert auf Klicks in der Steuerungsleiste. */
  _onControlClick(event) {
    if (!this._hass) return;
    const wlan = event.target.closest(".fbn-ctl-wlan");
    if (wlan) {
      this._hass.callService("switch", "toggle", { entity_id: wlan.dataset.entity });
      return;
    }
    const mac = event.target.closest(".fbn-ctl-mac");
    if (mac) {
      this._hass.callService("switch", "toggle", { entity_id: mac.dataset.entity });
      return;
    }
    const qrButton = event.target.closest(".fbn-ctl-gastwlan-qr");
    if (qrButton) {
      this._openGastWlanPopup();
      return;
    }
    // Pairing, Neu verbinden, Neustart (Box) und Neustart (Mesh) greifen tief in
    // die Netzwerkverbindung ein - ein versehentlicher Klick (Finger, Katze,
    // Touchscreen) darf sie nicht sofort auslösen. Alle vier verlangen deshalb
    // dieselbe Zwei-Klick-Bestaetigung: der erste Klick "schaerft" den Button
    // (Beschriftung wechselt zur Rueckfrage, 4 s Zeitfenster), erst der zweite
    // Klick loest die Aktion aus.
    const armable = event.target.closest(
      ".fbn-ctl-pairing, .fbn-ctl-reconnect, .fbn-ctl-reboot, .fbn-ctl-reboot-mesh"
    );
    if (armable) {
      const key = armable.classList.contains("fbn-ctl-reboot-mesh")
        ? "mesh_reboot"
        : armable.classList.contains("fbn-ctl-reboot")
        ? "reboot"
        : armable.classList.contains("fbn-ctl-reconnect")
        ? "reconnect"
        : "pairing";
      const label = `ctl.${key}`;
      const confirm = `ctl.${key}_confirm`;
      if (armable.dataset.armed !== "1") {
        armable.dataset.armed = "1";
        armable.classList.add("fbn-ctl-armed");
        armable.querySelector("span").textContent = this._t(confirm);
        clearTimeout(armable._fbnTimer);
        armable._fbnTimer = setTimeout(() => {
          armable.dataset.armed = "0";
          armable.classList.remove("fbn-ctl-armed");
          const span = armable.querySelector("span");
          if (span) span.textContent = this._t(label);
        }, 4000);
        return;
      }
      clearTimeout(armable._fbnTimer);
      armable.dataset.armed = "0";
      armable.classList.remove("fbn-ctl-armed");
      this._pressButton(armable);
    }
  }

  /** Uhrzeit (HH:MM, in der Sprache der Karte) aus einem ISO-Zeitstempel. */
  _formatTime(iso) {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "";
    try {
      return date.toLocaleTimeString(this._lang() || undefined, { hour: "2-digit", minute: "2-digit" });
    } catch (err) {
      return date.toTimeString().slice(0, 5);
    }
  }

  /** Loest einen Button-Entity aus und gibt kurze Rueckmeldung. */
  _pressButton(el) {
    const entity = el.dataset.entity;
    if (!entity) return;
    el.disabled = true;
    this._hass
      .callService("button", "press", { entity_id: entity })
      .then(() => {
        const span = el.querySelector("span");
        if (span) span.textContent = this._t("act.wol_sent");
        setTimeout(() => {
          el.disabled = false;
        }, 1500);
      })
      .catch(() => {
        el.disabled = false;
        const span = el.querySelector("span");
        if (span) span.textContent = this._t("act.failed");
      });
  }

  _renderBody() {
    const body = this.querySelector(".fbn-body");
    const empty = this.querySelector(".fbn-empty");
    if (!body) return;

    const state = this._stateObj();
    if (!state) {
      body.innerHTML = "";
      this._emptyWanted = true;
      if (empty) {
        empty.hidden = !this._networkVisible();
        empty.textContent = this._t("empty.sensor", { entity: this._config.entity });
      }
      return;
    }

    const hosts = this._filteredHosts();
    this._emptyWanted = hosts.length === 0;
    if (empty) {
      empty.hidden = !this._emptyWanted || !this._networkVisible();
      empty.textContent = this._t("empty.none");
    }

    const columns = this._visibleColumns();
    if (this._groupBy && hosts.length) {
      body.innerHTML = this._groupHosts(hosts)
        .map((group) => {
          const collapsed = this._collapsed.has(group.id);
          const label = String(this._groupLabel(this._groupBy, group) ?? "");
          const header = `<tr class="fbn-group-row" data-group="${escapeHtml(group.id)}"
              tabindex="0" role="button" aria-expanded="${collapsed ? "false" : "true"}">
              <td class="fbn-group-cell" colspan="${Math.max(columns.length, 1)}">
                <ha-icon icon="${collapsed ? "mdi:chevron-right" : "mdi:chevron-down"}"></ha-icon>
                <span class="fbn-group-name">${escapeHtml(label)}</span>
                <span class="fbn-group-count">${group.hosts.length}</span>
              </td></tr>`;
          return collapsed
            ? header
            : header + group.hosts.map((host) => this._renderRow(host, columns)).join("");
        })
        .join("");
    } else {
      body.innerHTML = hosts.map((host) => this._renderRow(host, columns)).join("");
    }

    if (!body.dataset.bound) {
      body.dataset.bound = "1";
      body.addEventListener("click", (event) => {
        // Klick auf den HA-Namen führt zum Home-Assistant-Gerät (SPA-Nav),
        // nicht ins Popup.
        const haLink = event.target.closest("a.fbn-halink");
        if (haLink) {
          event.preventDefault();
          this._openDevice(haLink.dataset.device);
          return;
        }
        // Klick auf die MAC-Adresse kopiert sie, oeffnet aber kein Popup.
        const macCell = event.target.closest(".fbn-maccopy");
        if (macCell) {
          event.stopPropagation();
          this._copyFromCell(macCell);
          return;
        }
        // Klick auf eine Gruppenüberschrift klappt die Gruppe auf/zu.
        const groupRow = event.target.closest("tr.fbn-group-row");
        if (groupRow) {
          this._toggleGroup(groupRow.dataset.group);
          return;
        }
        // Klick auf den IP-Link oeffnet die Weboberflaeche, nicht das Popup.
        if (event.target.closest("a")) return;
        const row = event.target.closest("tr[data-mac]");
        if (row) this._activateRow(row.dataset.mac, row);
      });
      body.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        const haLink = event.target.closest("a.fbn-halink");
        if (haLink) {
          event.preventDefault();
          this._openDevice(haLink.dataset.device);
          return;
        }
        // Enter/Leertaste auf der fokussierten MAC-Adresse kopiert sie.
        const macCell = event.target.closest(".fbn-maccopy");
        if (macCell) {
          event.preventDefault();
          event.stopPropagation();
          this._copyFromCell(macCell);
          return;
        }
        const groupRow = event.target.closest("tr.fbn-group-row");
        if (groupRow) {
          event.preventDefault();
          this._toggleGroup(groupRow.dataset.group);
          return;
        }
        // Enter auf dem fokussierten IP-Link folgt dem Link.
        if (event.target.closest("a")) return;
        const row = event.target.closest("tr[data-mac]");
        if (!row) return;
        event.preventDefault();
        this._activateRow(row.dataset.mac, row);
      });
    }

    // Nach jedem Neuaufbau kann sich die Gesamtbreite geaendert haben.
    this._updateArrows();
    this._applyMaxRows();
  }

  _toggleGroup(id) {
    if (!id) return;
    if (this._collapsed.has(id)) this._collapsed.delete(id);
    else this._collapsed.add(id);
    this._renderBody();
    this._saveView();
    // Fokus bleibt auf der Überschrift, damit die Tastatur weiter funktioniert.
    const again = Array.from(this.querySelectorAll("tr.fbn-group-row")).find((r) => r.dataset.group === id);
    if (again && again.focus) again.focus();
  }

  /**
   * Begrenzt die Höhe des Datenbereichs auf eine feste Zeilenzahl. Kopf,
   * Auswahl und Tabellenüberschrift bleiben stehen (die Überschrift ist
   * position:sticky), der Rest wird senkrecht scrollbar. Gemessen wird
   * die tatsächliche Höhe von Überschrift plus den ersten N Zeilen, damit
   * kompakte und normale Zeilen gleichermaßen passen.
   */
  _applyMaxRows() {
    const scroll = this._scrollEl;
    if (!scroll) return;
    const n = Number(this._config.max_visible_rows) || 0;
    if (n <= 0) {
      scroll.style.maxHeight = "";
      scroll.style.overflowY = "";
      return;
    }
    // Sobald begrenzt wird, ist senkrechtes Scrollen erlaubt.
    scroll.style.overflowY = "auto";
    const rows = scroll.querySelectorAll("tbody tr");
    if (!rows.length) {
      scroll.style.maxHeight = "";
      return;
    }
    const thead = scroll.querySelector("thead");
    let height = thead ? thead.offsetHeight : 0;
    const count = Math.min(n, rows.length);
    for (let i = 0; i < count; i += 1) height += rows[i].offsetHeight;
    // Nur setzen, wenn tatsächlich messbar (Karte sichtbar). Sonst später
    // beim nächsten Render/Resize erneut versuchen.
    if (height > 0) scroll.style.maxHeight = `${height}px`;
  }

  /**
   * Reagiert auf Klick oder Tastendruck einer Zeile. Vorrang hat das
   * Detail-Popup (dort steht auch die MAC-Adresse, die in der schmalen
   * Tabelle ausgeblendet sein kann). Ist das Popup abgeschaltet, gilt
   * das bisherige Verhalten: sofort das Home-Assistant-Geraet oeffnen.
   */
  _activateRow(mac, rowEl) {
    if (this._config.show_details_popup) {
      const host = this._hosts().find((item) => item.mac === mac);
      if (host) this._openPopup(host, rowEl);
      return;
    }
    if (this._config.open_device_on_click) {
      const host = this._hosts().find((item) => item.mac === mac);
      if (host && host.ha_device_id) this._openDevice(host.ha_device_id);
    }
  }

  /** Ob ein Zeilenklick ueberhaupt etwas ausloest. */
  _rowInteractive(host) {
    if (this._config.show_details_popup) return true;
    return this._config.open_device_on_click && !!host.ha_device_id;
  }

  _renderRow(host, columns) {
    const macAttr = ` data-mac="${escapeHtml(host.mac)}"`;
    const interactive = this._rowInteractive(host);
    const classes = ["fbn-tr"];
    if (!host.active) classes.push("fbn-inactive");
    let extra = "";
    if (interactive) {
      classes.push("fbn-clickable");
      extra = ' tabindex="0" role="button"';
    }
    const cells = columns
      .map(
        (column) =>
          `<td class="fbn-td fbn-col-${column.key} fbn-prio-${column.prio}" style="text-align:${
            column.align || "left"
          }">${this._renderCell(host, column.key)}</td>`
      )
      .join("");
    return `<tr class="${classes.join(" ")}"${macAttr}${extra}>${cells}</tr>`;
  }

  _renderCell(host, key) {
    switch (key) {
      case "status":
        return `<span class="fbn-dot ${
          host.active ? "fbn-dot-on" : "fbn-dot-off"
        }" title="${host.active ? this._t("state.connected") : this._t("state.disconnected")}"></span>`;

      case "name": {
        const badges = [];
        if (host.guest) badges.push(`<span class="fbn-badge fbn-badge-guest">${escapeHtml(this._t("badge.guest"))}</span>`);
        if (host.vpn) badges.push(`<span class="fbn-badge">${escapeHtml(this._t("badge.vpn"))}</span>`);
        if (host.priority) badges.push(`<span class="fbn-badge">${escapeHtml(this._t("badge.priority"))}</span>`);
        return `
          <div class="fbn-namecell">
            <ha-icon class="fbn-rowicon" icon="${connectionIcon(host)}"></ha-icon>
            <span class="fbn-name">${escapeHtml(host.name)}</span>
            ${badges.join("")}
          </div>`;
      }

      case "ip": {
        const plain = `<span class="fbn-mono">${escapeHtml(host.ip || "—")}</span>`;
        if (!host.ip || !this._config.ip_opens_web) return plain;
        const url = webUrl(host, this._config.ip_web_fallback);
        if (!url) return plain;
        // Der Link oeffnet die Weboberflaeche in einem neuen Tab. Der
        // Klick darauf darf NICHT zusaetzlich das Zeilen-Popup oeffnen -
        // das faengt der Zeilen-Handler ueber "closest('a')" ab.
        return `<a class="fbn-iplink fbn-mono" href="${escapeHtml(url)}"
                   target="_blank" rel="noopener noreferrer"
                   title="${escapeHtml(this._t('tip.web', { url }))}"
                   aria-label="${escapeHtml(this._t('btn.web'))}"
                >${escapeHtml(host.ip)}<ha-icon class="fbn-iplink-icon" icon="mdi:open-in-new"></ha-icon></a>`;
      }

      case "mac": {
        if (!host.mac) return '<span class="fbn-mono fbn-dim">—</span>';
        if (!this._config.mac_click_copies) {
          return `<span class="fbn-mono fbn-dim">${escapeHtml(host.mac)}</span>`;
        }
        // Klick kopiert die Adresse; der Zeilen-Handler öffnet dann NICHT
        // zusätzlich das Popup (siehe "fbn-maccopy" in _renderBody).
        return `<span class="fbn-mono fbn-dim fbn-maccopy" role="button" tabindex="0"
                      data-copy="${escapeHtml(host.mac)}"
                      title="${escapeHtml(this._t("tip.copy"))}">${escapeHtml(host.mac)}</span>`;
      }

      case "band": {
        const label = this._bandLabel(host);
        return label ? `<span>${escapeHtml(label)}</span>` : '<span class="fbn-dim">—</span>';
      }

      case "connected_via": {
        if (!host.connected_via) return '<span class="fbn-dim">—</span>';
        const rate = host.link_mbit ? ` (${formatSpeed(host.link_mbit)})` : "";
        return `<span title="${escapeHtml(host.connected_via + rate)}">${escapeHtml(
          host.connected_via
        )}</span>`;
      }

      case "vendor":
        if (host.vendor) return `<span class="fbn-vendor">${escapeHtml(host.vendor)}</span>`;
        if (host.mac_random) {
          return `<span class="fbn-dim" title="${escapeHtml(
            this._t("vendor.random_tip")
          )}">${escapeHtml(this._t("vendor.random"))}</span>`;
        }
        return '<span class="fbn-dim">—</span>';

      case "label":
        return host.label
          ? `<span class="fbn-label-chip">${escapeHtml(host.label)}</span>`
          : '<span class="fbn-dim">—</span>';

      case "note": {
        if (!host.note) return '<span class="fbn-dim">—</span>';
        const short = host.note.length > 60 ? `${host.note.slice(0, 57)}…` : host.note;
        return `<span class="fbn-note-text" title="${escapeHtml(host.note)}">${escapeHtml(
          short.replace(/\s*\n\s*/g, " ")
        )}</span>`;
      }

      case "connection":
        return escapeHtml(this._connLabel(host));

      case "ha_name": {
        if (!host.ha_name) return '<span class="fbn-dim">—</span>';
        if (host.ha_device_id) {
          // Link zur Home-Assistant-Geräteseite. Wie beim IP-Link fängt
          // der Zeilen-Handler den Klick ab, sodass NICHT zusätzlich das
          // Popup aufgeht; die SPA-Navigation macht _openDevice per JS.
          return `<a class="fbn-halink" href="/config/devices/device/${escapeHtml(
            host.ha_device_id
          )}" data-device="${escapeHtml(host.ha_device_id)}"
                    title="${escapeHtml(this._t('tip.ha'))}">${escapeHtml(host.ha_name)}</a>`;
        }
        return `<span class="fbn-ha">${escapeHtml(host.ha_name)}</span>`;
      }

      case "ip_type": {
        const compact = this._config.compact;
        const days = this._leaseDays(host.lease_time_remaining);
        if (host.ip_class === "fixed") {
          return `<span class="fbn-badge fbn-badge-static">${escapeHtml(this._t("iptype.fixed"))}</span>`;
        }
        if (host.ip_class === "dynamic") {
          // Kompakt: "dyn. 10" (Tage); normal: "dynamisch (noch 10 Tage)".
          const lease = formatLease(host.lease_time_remaining);
          const label = compact ? this._t("iptype.dyn_short") : this._t("iptype.dynamic");
          if (compact) {
            return `<span class="fbn-dim" title="${escapeHtml(
              lease || this._t("iptype.dynamic")
            )}">${escapeHtml(label)}${days ? ` ${days}` : ""}</span>`;
          }
          return `<span class="fbn-dim">${escapeHtml(label)}${
            lease ? ` <span class="fbn-lease">(${escapeHtml(lease)})</span>` : ""
          }</span>`;
        }
        if (host.ip_class === "none") {
          return `<span class="fbn-dim" title="${escapeHtml(this._t("iptype.noip"))}">—</span>`;
        }
        return '<span class="fbn-dim">—</span>';
      }

      case "wan":
        return host.blocked
          ? `<ha-icon class="fbn-icon-blocked" icon="mdi:web-off" title="${escapeHtml(this._t("tip.blocked"))}"></ha-icon>`
          : '<span class="fbn-dim">—</span>';

      case "update":
        return host.update_available
          ? `<ha-icon class="fbn-icon-update" icon="mdi:package-down" title="${escapeHtml(this._t("tip.update"))}"></ha-icon>`
          : '<span class="fbn-dim">—</span>';

      case "speed": {
        const text = this._config.compact
          ? formatSpeedCompact(host.speed)
          : formatSpeed(host.speed);
        const title =
          this._config.compact && host.speed
            ? ` title="${escapeHtml(formatSpeed(host.speed))}"`
            : "";
        return `<span class="fbn-mono fbn-dim"${title}>${escapeHtml(text)}</span>`;
      }

      case "model":
        return escapeHtml(host.model || "—");

      case "type":
        return escapeHtml(host.device_class_user || host.device_class || "—");

      case "last_seen": {
        if (host.active) {
          return `<span class="fbn-ls-now" title="${escapeHtml(this._t("tip.online"))}">${escapeHtml(this._t("state.online_now"))}</span>`;
        }
        const text = formatLastSeen(host.last_seen, this._lang());
        const title = host.last_seen
          ? this._t("tip.ls_last", { ts: host.last_seen })
          : this._t("tip.ls_unknown");
        return `<span class="fbn-dim" title="${escapeHtml(title)}">${escapeHtml(text)}</span>`;
      }

      default:
        return "";
    }
  }

  /** Oeffnet die Geraeteseite in Home Assistant. */
  _openDevice(deviceId) {
    if (!deviceId) return;
    const path = `/config/devices/device/${deviceId}`;
    history.pushState(null, "", path);
    window.dispatchEvent(new Event("location-changed"));
  }

  /* -- Detail-Popup ------------------------------------------------- */

  /**
   * Oeffnet das Detail-Popup fuer ein Geraet. Der Overlay-Knoten wird
   * bewusst an document.body gehaengt (nicht in die Karte), damit er
   * ueber allem liegt, egal in welchem Stapelkontext die Karte steckt.
   */
  _openPopup(host, returnFocusEl) {
    this._closePopup();
    this._popupMac = host.mac;
    this._popupReturnFocus = returnFocusEl || null;
    this._popupEditingName = false;
    this._popupNameDraft = "";
    this._popupEditingNote = false;
    this._popupNoteDraft = null;
    this._parental = null;

    const overlay = document.createElement("div");
    overlay.className = "fbn-overlay";
    overlay.innerHTML = `
      <style>${this._popupStyles()}</style>
      <div class="fbn-modal" role="dialog" aria-modal="true"
           aria-label="${escapeHtml(this._t('popup.aria', { name: host.name }))}">
        <div class="fbn-modal-head">
          <ha-icon class="fbn-modal-icon" icon="${connectionIcon(host)}"></ha-icon>
          <div class="fbn-modal-titles">
            <div class="fbn-modal-title"></div>
            <div class="fbn-modal-sub"></div>
          </div>
          <button class="fbn-modal-close" type="button" aria-label="${escapeHtml(this._t('btn.close'))}">
            <ha-icon icon="mdi:close"></ha-icon>
          </button>
        </div>
        <div class="fbn-modal-body"></div>
        <div class="fbn-modal-foot"></div>
      </div>`;
    document.body.appendChild(overlay);
    this._popup = overlay;

    // Schliessen ueber Klick auf den Hintergrund, aber nicht auf den
    // Dialog selbst.
    overlay.addEventListener("mousedown", (event) => {
      if (event.target === overlay) this._closePopup();
    });

    this._onPopupKeydown = (event) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        // Waehrend der Namensbearbeitung soll Escape nur die Eingabe
        // verwerfen (auch wenn der Fokus auf Speichern/Abbrechen steht,
        // nicht im Eingabefeld selbst) - nicht das ganze Popup schliessen.
        if (this._popupEditingName) {
          const host = this._hosts().find((item) => item.mac === this._popupMac);
          if (host) this._cancelNameEdit(host);
          return;
        }
        if (this._popupEditingNote) {
          const host = this._hosts().find((item) => item.mac === this._popupMac);
          if (host) this._cancelNoteEdit(host);
          return;
        }
        this._closePopup();
      }
    };
    overlay.addEventListener("keydown", this._onPopupKeydown);

    overlay
      .querySelector(".fbn-modal-close")
      .addEventListener("click", () => this._closePopup());

    this._refreshPopup();

    const close = overlay.querySelector(".fbn-modal-close");
    if (close && close.focus) close.focus();
  }

  /** Baut den Inhalt des Popups aus den jeweils aktuellen Daten neu auf. */
  _refreshPopup() {
    if (!this._popup) return;
    const host =
      this._hosts().find((item) => item.mac === this._popupMac) || null;
    if (!host) {
      // Geraet ist aus der Liste verschwunden - Popup mit Hinweis lassen,
      // aber nicht abrupt schliessen.
      const body = this._popup.querySelector(".fbn-modal-body");
      if (body && !body.dataset.gone) {
        body.dataset.gone = "1";
        const note = document.createElement("div");
        note.className = "fbn-modal-note";
        note.textContent = this._t("popup.gone");
        body.prepend(note);
      }
      return;
    }
    // Waehrend der Nutzer einen neuen Namen eingibt, wird das Popup NICHT
    // neu aufgebaut - sonst ginge die Eingabe bei jedem Hintergrund-Update
    // (Polling, i. d. R. alle paar Sekunden bis Minuten) verloren. Speichern
    // und Abbrechen bauen danach ausdruecklich ueber _renderPopupContent()
    // neu auf, an dieser Bremse vorbei.
    if (this._popupEditingName || this._popupEditingNote) return;
    this._renderPopupContent(host);
  }

  /** Baut Titel, Zeilen und Fusszeile des Popups fuer ein Geraet neu auf. */
  _renderPopupContent(host) {
    const title = this._popup.querySelector(".fbn-modal-title");
    const sub = this._popup.querySelector(".fbn-modal-sub");
    title.textContent = host.name;
    sub.innerHTML = `
      <span class="fbn-dot ${host.active ? "fbn-dot-on" : "fbn-dot-off"}"></span>
      ${host.active ? escapeHtml(this._t("state.connected")) : escapeHtml(this._t("state.disconnected"))} · ${escapeHtml(
      this._connLabel(host)
    )}`;

    this._popup.querySelector(".fbn-modal-body").innerHTML =
      this._popupRows(host);
    this._popup.querySelector(".fbn-modal-foot").innerHTML =
      this._popupButtons(host);

    // Kopier-Knoepfe verkabeln.
    this._popup.querySelectorAll(".fbn-copy").forEach((button) => {
      button.addEventListener("click", () => this._copy(button.dataset.copy, button));
    });

    // Device-Tracker-Link: oeffnet den Info-Dialog der Entitaet.
    const trackerLink = this._popup.querySelector(".fbn-tracker-link");
    if (trackerLink) {
      trackerLink.addEventListener("click", (event) => {
        event.preventDefault();
        this.dispatchEvent(
          new CustomEvent("hass-more-info", {
            detail: { entityId: trackerLink.dataset.entity },
            bubbles: true,
            composed: true,
          })
        );
        this._closePopup();
      });
    }

    // Home Assistant oeffnen.
    const haButton = this._popup.querySelector(".fbn-act-ha");
    if (haButton) {
      haButton.addEventListener("click", () => {
        this._closePopup();
        this._openDevice(host.ha_device_id);
      });
    }

    // Wake-on-LAN.
    const wolButton = this._popup.querySelector(".fbn-act-wol");
    if (wolButton) {
      wolButton.addEventListener("click", () => this._wakeDevice(host, wolButton));
    }

    // Internetzugang sperren/freigeben.
    const inetButton = this._popup.querySelector(".fbn-act-inet");
    if (inetButton) {
      inetButton.addEventListener("click", () =>
        this._setInternet(host, inetButton)
      );
    }

    // Umbenennen: Stift startet die Bearbeitung, das Eingabefeld merkt sich
    // den Entwurf laufend, Haken/Enter speichert, Kreuz/Escape verwirft.
    const nameEditBtn = this._popup.querySelector(".fbn-name-edit-btn");
    if (nameEditBtn) {
      nameEditBtn.addEventListener("click", () => {
        this._popupEditingName = true;
        this._popupNameDraft = host.name;
        this._renderPopupContent(host);
        const input = this._popup.querySelector(".fbn-name-input");
        if (input) {
          input.focus();
          input.select();
        }
      });
    }
    const nameInput = this._popup.querySelector(".fbn-name-input");
    if (nameInput) {
      nameInput.addEventListener("input", () => {
        this._popupNameDraft = nameInput.value;
      });
      nameInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          this._saveDeviceName(host);
        } else if (event.key === "Escape") {
          // Nicht das ganze Popup schliessen (das macht der Handler am
          // Overlay) - nur die Bearbeitung verwerfen.
          event.stopPropagation();
          this._cancelNameEdit(host);
        }
      });
    }
    const nameSaveBtn = this._popup.querySelector(".fbn-name-save");
    if (nameSaveBtn) {
      nameSaveBtn.addEventListener("click", () => this._saveDeviceName(host));
    }
    const nameCancelBtn = this._popup.querySelector(".fbn-name-cancel");
    if (nameCancelBtn) {
      nameCancelBtn.addEventListener("click", () => this._cancelNameEdit(host));
    }

    // Etikett/Notiz bearbeiten (Idee 3): Stift startet, Haken speichert,
    // Kreuz/Escape verwirft; der Entwurf bleibt bei Hintergrund-Updates erhalten.
    const noteEditBtn = this._popup.querySelector(".fbn-note-edit-btn");
    if (noteEditBtn) {
      noteEditBtn.addEventListener("click", () => {
        this._popupEditingNote = true;
        this._popupNoteDraft = {
          label: host.label || "",
          note: host.note || "",
          reserved: !!host.reserved,
        };
        this._renderPopupContent(host);
        const input = this._popup.querySelector(".fbn-note-label-input");
        if (input) input.focus();
      });
    }
    const noteLabelInput = this._popup.querySelector(".fbn-note-label-input");
    const noteTextInput = this._popup.querySelector(".fbn-note-text-input");
    const noteReservedInput = this._popup.querySelector(".fbn-note-reserved-input");
    if (noteLabelInput) {
      noteLabelInput.addEventListener("input", () => {
        this._popupNoteDraft.label = noteLabelInput.value;
      });
    }
    if (noteTextInput) {
      noteTextInput.addEventListener("input", () => {
        this._popupNoteDraft.note = noteTextInput.value;
      });
    }
    if (noteReservedInput) {
      noteReservedInput.addEventListener("change", () => {
        this._popupNoteDraft.reserved = noteReservedInput.checked;
      });
    }
    const noteSaveBtn = this._popup.querySelector(".fbn-note-save");
    if (noteSaveBtn) noteSaveBtn.addEventListener("click", () => this._saveNote(host));
    const noteCancelBtn = this._popup.querySelector(".fbn-note-cancel");
    if (noteCancelBtn) noteCancelBtn.addEventListener("click", () => this._cancelNoteEdit(host));

    // Zugangsprofil (Kindersicherung): Laden, Auswahl, Übernehmen.
    const profLoad = this._popup.querySelector(".fbn-prof-load");
    if (profLoad) profLoad.addEventListener("click", () => this._loadProfiles(host));
    const profSelect = this._popup.querySelector(".fbn-prof-select");
    if (profSelect) {
      profSelect.addEventListener("change", () => {
        if (this._parental) this._parental.draftProfile = profSelect.value;
      });
    }
    const profMinutes = this._popup.querySelector(".fbn-prof-minutes");
    if (profMinutes) {
      profMinutes.addEventListener("input", () => {
        if (this._parental) this._parental.draftMinutes = profMinutes.value;
      });
    }
    const profApply = this._popup.querySelector(".fbn-prof-apply");
    if (profApply) profApply.addEventListener("click", () => this._applyProfile(host));

    // Schliessen in der Fusszeile.
    const footClose = this._popup.querySelector(".fbn-modal-close2");
    if (footClose) footClose.addEventListener("click", () => this._closePopup());
  }

  /** Bricht die Namensbearbeitung im Popup ab, ohne zu speichern. */
  _cancelNameEdit(host) {
    this._popupEditingName = false;
    this._popupNameDraft = "";
    this._renderPopupContent(host);
  }

  /**
   * Speichert den im Popup eingegebenen neuen Geraetenamen ueber den Dienst
   * ``fritzbox_netzwerk.set_device_name``. Der Coordinator fragt danach
   * selbst neu ab (siehe __init__.py); bis die Antwort da ist, zeigt das
   * Popup den eingegebenen Namen schon an, ohne die Kartendaten selbst zu
   * aendern - das naechste reguläre Update bringt den bestaetigten Stand.
   */
  _saveDeviceName(host) {
    if (!this._hass || !host.mac) return;
    const input = this._popup && this._popup.querySelector(".fbn-name-input");
    const value = (input ? input.value : this._popupNameDraft || "").trim();
    if (!value || value === host.name) {
      // Nichts zu speichern (leer oder unveraendert) - nur die Eingabe
      // schliessen, ohne die FRITZ!Box anzusprechen.
      this._cancelNameEdit(host);
      return;
    }
    if (input) input.disabled = true;
    const saveBtn = this._popup.querySelector(".fbn-name-save");
    const cancelBtn = this._popup.querySelector(".fbn-name-cancel");
    if (saveBtn) saveBtn.disabled = true;
    if (cancelBtn) cancelBtn.disabled = true;
    this._hass
      .callService("fritzbox_netzwerk", "set_device_name", {
        mac: host.mac,
        name: value,
      })
      .then(() => {
        this._popupEditingName = false;
        this._popupNameDraft = "";
        const wrap = this._popup && this._popup.querySelector(".fbn-name-edit");
        if (wrap) {
          wrap.outerHTML = `${escapeHtml(value)}<span class="fbn-namebtn fbn-name-saved" aria-hidden="true"><ha-icon icon="mdi:check"></ha-icon></span>`;
        }
        const title = this._popup && this._popup.querySelector(".fbn-modal-title");
        if (title) title.textContent = value;
      })
      .catch(() => {
        if (input) input.disabled = false;
        if (saveBtn) saveBtn.disabled = false;
        if (cancelBtn) cancelBtn.disabled = false;
        this.dispatchEvent(
          new CustomEvent("hass-notification", {
            detail: { message: this._t("act.failed") },
            bubbles: true,
            composed: true,
          })
        );
      });
  }

  _cancelNoteEdit(host) {
    this._popupEditingNote = false;
    this._popupNoteDraft = null;
    this._renderPopupContent(host);
  }

  /**
   * Speichert Etikett, Notiz und "reserviert" über den Dienst
   * ``fritzbox_netzwerk.set_device_note``. Gespeichert wird nur in Home
   * Assistant, die FRITZ!Box wird nicht angesprochen. Der Coordinator
   * aktualisiert die Hostliste sofort; bis dahin zeigt das Popup den Entwurf.
   */
  _saveNote(host) {
    if (!this._hass || !host.mac || !this._popupNoteDraft) return;
    const draft = this._popupNoteDraft;
    const buttons = this._popup.querySelectorAll(
      ".fbn-note-save, .fbn-note-cancel, .fbn-note-form input, .fbn-note-form textarea"
    );
    buttons.forEach((el) => {
      el.disabled = true;
    });
    this._hass
      .callService("fritzbox_netzwerk", "set_device_note", {
        mac: host.mac,
        label: draft.label,
        note: draft.note,
        reserved: !!draft.reserved,
      })
      .then(() => {
        this._popupEditingNote = false;
        this._popupNoteDraft = null;
        // Lokal sofort übernehmen; das nächste Sensor-Update bestätigt es.
        host.label = String(draft.label || "").trim();
        host.note = String(draft.note || "").trim();
        host.reserved = !!draft.reserved;
        this._renderPopupContent(host);
      })
      .catch(() => {
        buttons.forEach((el) => {
          el.disabled = false;
        });
        this.dispatchEvent(
          new CustomEvent("hass-notification", {
            detail: { message: this._t("act.failed") },
            bubbles: true,
            composed: true,
          })
        );
      });
  }

  /* -- Kindersicherung im Popup (Zugangsprofile) -------------------------
   *
   * Nutzt die Dienste fritzbox_netzwerk.get_access_profile / set_access_profile (Antwort per
   * ``callService(..., returnResponse)``). Nichts wird automatisch geladen: jede Abfrage meldet
   * sich an der Weboberfläche der Box an, deshalb erst auf Klick. Geschrieben wird nur über
   * „Übernehmen"; mit Minuten stellt die Integration das bisherige Profil selbst wieder her.
   */
  _parentalEnabled() {
    const state = this._stateObj();
    const attributes = (state && state.attributes) || {};
    return this._config.show_parental !== false && attributes.parental === true;
  }

  _profileName(profile) {
    return (profile && (profile.name || profile.id)) || this._t("prof.unknown");
  }

  _parentalRowsHtml(host) {
    if (!this._hass || !host.mac || !this._parentalEnabled()) return "";
    const t = (key, params) => escapeHtml(this._t(key, params));
    const st = this._parental && this._parental.mac === host.mac ? this._parental : null;
    const row = (inner) =>
      `<div class="fbn-drow fbn-prof-row"><div class="fbn-dt">${t("prof.title")}</div><div class="fbn-dd fbn-prof-box">${inner}</div></div>`;
    const warn = `<div class="fbn-prof-hint">${t("prof.warn")}</div>`;
    const loadBtn = (label) =>
      `<button class="fbn-prof-btn fbn-prof-load" type="button" title="${t("prof.load_tip")}">
         <ha-icon icon="mdi:shield-account-outline"></ha-icon>${escapeHtml(label)}</button>`;
    if (!st || st.status === "idle") return row(`${loadBtn(this._t("prof.load"))}${warn}`);
    if (st.status === "loading") return row(`<span>${t("prof.loading")}</span>`);
    if (st.status === "error") {
      return row(
        `<span class="fbn-prof-err">${t("prof.error", { error: String(st.error || "") })}</span>${loadBtn(
          this._t("prof.retry")
        )}`
      );
    }
    const saving = st.status === "saving";
    const options = (st.profiles || [])
      .map(
        (p) =>
          `<option value="${escapeHtml(p.id)}"${p.id === st.draftProfile ? " selected" : ""}>${escapeHtml(
            p.name || p.id
          )}</option>`
      )
      .join("");
    const current = (st.profiles || []).find((p) => p.id === st.current);
    const revert = st.revertTo
      ? `<div class="fbn-prof-hint">${t("prof.revert", {
          name: this._profileName((st.profiles || []).find((p) => p.id === st.revertTo) || { id: st.revertTo }),
          time: this._formatTime(st.revertAt),
        })}</div>`
      : "";
    return row(`
      <span class="fbn-prof-current">${t("prof.current", { name: this._profileName(current || { name: st.currentName }) })}</span>
      <div class="fbn-prof-line">
        <select class="fbn-prof-select" aria-label="${t("prof.title")}"${saving ? " disabled" : ""}>${options}</select>
        <input class="fbn-prof-minutes" type="number" min="1" max="10080" inputmode="numeric"
               placeholder="${t("prof.minutes")}" aria-label="${t("prof.minutes")}"
               value="${escapeHtml(st.draftMinutes || "")}"${saving ? " disabled" : ""}>
        <button class="fbn-prof-btn fbn-prof-apply" type="button" title="${t("prof.apply_tip")}"${saving ? " disabled" : ""}>
          <ha-icon icon="mdi:check"></ha-icon>${t("prof.apply")}</button>
      </div>
      <div class="fbn-prof-hint">${t("prof.minutes_hint")}</div>${revert}${warn}`);
  }

  _parentalNotify(message) {
    this.dispatchEvent(
      new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true })
    );
  }

  /** Lädt aktuelles Profil und Profilliste des Geräts (eine Anmeldung an der Box). */
  _loadProfiles(host) {
    if (!this._hass || !host.mac) return;
    const previous = this._parental && this._parental.mac === host.mac ? this._parental : {};
    this._parental = { ...previous, mac: host.mac, status: "loading" };
    this._renderPopupContent(host);
    this._hass
      .callService("fritzbox_netzwerk", "get_access_profile", { mac: host.mac }, undefined, true, true)
      .then((result) => {
        if (this._popupMac !== host.mac || !this._parental) return;
        const r = (result && result.response) || {};
        const profiles = Array.isArray(r.profile_liste) ? r.profile_liste : [];
        this._parental = {
          mac: host.mac,
          status: "ready",
          profiles,
          current: r.profile || "",
          currentName: r.name || "",
          revertTo: r.zurueck_auf || "",
          revertAt: r.zurueck_um || "",
          draftProfile: r.profile || (profiles[0] && profiles[0].id) || "",
          draftMinutes: "",
        };
        this._renderPopupContent(host);
      })
      .catch((err) => this._parentalFailed(host, err));
  }

  _parentalFailed(host, err) {
    if (this._popupMac !== host.mac) return;
    this._parental = {
      ...(this._parental || {}),
      mac: host.mac,
      status: "error",
      error: String((err && (err.message || err.error)) || err || ""),
    };
    this._renderPopupContent(host);
  }

  /** Weist das gewählte Profil zu (optional nur für N Minuten) und lädt den Stand neu. */
  _applyProfile(host) {
    const st = this._parental;
    if (!this._hass || !st || st.mac !== host.mac || !st.draftProfile) return;
    const data = { mac: host.mac, profile: st.draftProfile };
    const minutes = parseInt(st.draftMinutes, 10);
    if (Number.isFinite(minutes) && minutes > 0) data.minutes = Math.min(minutes, 10080);
    const chosen = (st.profiles || []).find((p) => p.id === st.draftProfile);
    this._parental = { ...st, status: "saving" };
    this._renderPopupContent(host);
    this._hass
      .callService("fritzbox_netzwerk", "set_access_profile", data, undefined, true, true)
      .then(() => {
        this._parentalNotify(this._t("prof.saved", { name: this._profileName(chosen) }));
        if (this._popupMac === host.mac) this._loadProfiles(host);
      })
      .catch((err) => {
        if (this._popupMac !== host.mac) return;
        this._parental = { ...st, status: "ready" };
        this._parentalFailed(host, err);
      });
  }

  /** Etikett-, Notiz- und Reserviert-Zeilen des Popups (Idee 3). */
  _noteRowsHtml(host) {
    if (!this._hass) return "";
    const t = (key) => escapeHtml(this._t(key));
    if (this._popupEditingNote && this._popupNoteDraft) {
      const d = this._popupNoteDraft;
      return `
        <div class="fbn-drow fbn-note-form">
          <div class="fbn-dt">${t("field.label")} / ${t("field.note")}</div>
          <div class="fbn-dd fbn-note-fields">
            <input class="fbn-note-label-input" type="text" maxlength="40"
                   value="${escapeHtml(d.label)}" placeholder="${t("note.label_placeholder")}"
                   aria-label="${t("field.label")}">
            <textarea class="fbn-note-text-input" rows="3" maxlength="500"
                      placeholder="${t("note.text_placeholder")}"
                      aria-label="${t("field.note")}">${escapeHtml(d.note)}</textarea>
            <label class="fbn-note-reserved">
              <input class="fbn-note-reserved-input" type="checkbox"${d.reserved ? " checked" : ""}>
              <span>${t("note.reserved")}</span>
            </label>
            <div class="fbn-note-hint">${t("note.reserved_hint")}</div>
            <div class="fbn-note-actions">
              <button class="fbn-namebtn fbn-note-save" type="button"
                      title="${t("btn.save")}" aria-label="${t("btn.save")}">
                <ha-icon icon="mdi:check"></ha-icon></button>
              <button class="fbn-namebtn fbn-note-cancel" type="button"
                      title="${t("btn.cancel")}" aria-label="${t("btn.cancel")}">
                <ha-icon icon="mdi:close"></ha-icon></button>
            </div>
          </div>
        </div>`;
    }
    const edit = `<button class="fbn-namebtn fbn-note-edit-btn" type="button"
        title="${t("btn.edit_note")}" aria-label="${t("btn.edit_note")}">
        <ha-icon icon="mdi:pencil"></ha-icon></button>`;
    const label = host.label
      ? `<span class="fbn-label-chip">${escapeHtml(host.label)}</span>`
      : "—";
    const note = host.note
      ? `<span class="fbn-note-full">${escapeHtml(host.note)}</span>`
      : "—";
    const reserved = host.reserved
      ? `<div class="fbn-drow"><div class="fbn-dt">${t("field.reserved")}</div><div class="fbn-dd">${t(
          "note.reserved_yes"
        )}</div></div>`
      : "";
    return `
      <div class="fbn-drow"><div class="fbn-dt">${t("field.label")}</div><div class="fbn-dd">${label}${edit}</div></div>
      <div class="fbn-drow"><div class="fbn-dt">${t("field.note")}</div><div class="fbn-dd">${note}</div></div>
      ${reserved}`;
  }

  /**
   * HTML fuer die Namenszeile im Popup: reiner Text, wenn die FRITZ!Box den
   * Namen nicht ueber TR-064 aendern laesst (``name_writeable``); sonst Text
   * mit Stift-Knopf, bzw. - waehrend der Bearbeitung - ein Eingabefeld mit
   * Speichern/Abbrechen.
   */
  _nameFieldHtml(host) {
    if (!host.name_writeable) return escapeHtml(host.name);
    if (this._popupEditingName) {
      return `
        <span class="fbn-name-edit">
          <input class="fbn-name-input" type="text"
                 value="${escapeHtml(this._popupNameDraft)}" maxlength="64"
                 aria-label="${escapeHtml(this._t("field.name"))}">
          <button class="fbn-namebtn fbn-name-save" type="button"
                  title="${escapeHtml(this._t("btn.save"))}"
                  aria-label="${escapeHtml(this._t("btn.save"))}">
            <ha-icon icon="mdi:check"></ha-icon>
          </button>
          <button class="fbn-namebtn fbn-name-cancel" type="button"
                  title="${escapeHtml(this._t("btn.cancel"))}"
                  aria-label="${escapeHtml(this._t("btn.cancel"))}">
            <ha-icon icon="mdi:close"></ha-icon>
          </button>
        </span>`;
    }
    return `${escapeHtml(host.name)}<button class="fbn-namebtn fbn-name-edit-btn" type="button"
              title="${escapeHtml(this._t("btn.rename"))}"
              aria-label="${escapeHtml(this._t("btn.rename"))}">
              <ha-icon icon="mdi:pencil"></ha-icon></button>`;
  }

  /** Definitionsliste aller Felder eines Geraets. */
  _popupRows(host) {
    const rows = [];
    const add = (label, value, options) => {
      const opts = options || {};
      const shown =
        value === null || value === undefined || value === "" ? "—" : value;
      const copy =
        opts.copy && shown !== "—"
          ? `<button class="fbn-copy" type="button" data-copy="${escapeHtml(
              opts.copy
            )}" aria-label="${escapeHtml(this._t('copy.aria', { label }))}"><ha-icon icon="mdi:content-copy"></ha-icon></button>`
          : "";
      rows.push(`
        <div class="fbn-drow">
          <div class="fbn-dt">${escapeHtml(label)}</div>
          <div class="fbn-dd${opts.mono ? " fbn-mono" : ""}">${shown}${copy}</div>
        </div>`);
    };

    add(this._t("field.name"), this._nameFieldHtml(host));
    const noteRows = this._noteRowsHtml(host);
    if (noteRows) rows.push(noteRows);
    const parentalRows = this._parentalRowsHtml(host);
    if (parentalRows) rows.push(parentalRows);
    add(this._t("col.ip"), escapeHtml(host.ip), { mono: true, copy: host.ip });
    add(this._t("col.mac"), escapeHtml(host.mac), { mono: true, copy: host.mac });
    add(
      this._t("field.vendor"),
      host.vendor
        ? escapeHtml(host.vendor)
        : host.mac_random
        ? `<span title="${escapeHtml(this._t("vendor.random_tip"))}">${escapeHtml(
            this._t("vendor.random")
          )}</span>`
        : ""
    );
    add(this._t("col.connection"), escapeHtml(this._connLabel(host)));
    if (host.band) add(this._t("field.band"), escapeHtml(this._bandLabel(host)));
    if (host.connected_via) {
      const rate = host.link_mbit ? ` (${formatSpeed(host.link_mbit)})` : "";
      add(this._t("field.connected_via"), escapeHtml(host.connected_via + rate));
    }
    add(
      this._t("field.status"),
      host.active ? this._t("state.connected") : this._t("state.disconnected")
    );

    let ipType = "—";
    if (host.ip_class === "fixed") {
      ipType = this._t("iptype.fixed");
    } else if (host.ip_class === "dynamic") {
      const lease = formatLease(host.lease_time_remaining);
      const dyn = this._t("iptype.dynamic");
      ipType = lease ? `${dyn} (${escapeHtml(lease)})` : dyn;
    } else if (host.ip_class === "none") {
      ipType = this._t("iptype.noip");
    }
    add(this._t("field.ip_type"), ipType);

    add(this._t("field.speed"), host.active ? escapeHtml(formatSpeed(host.speed)) : "—");
    add(this._t("field.wan"), host.blocked ? this._t("wan.blocked") : this._t("wan.allowed"));
    if (host.filter_profile) add(this._t("field.filter_profile"), escapeHtml(host.filter_profile));
    add(this._t("field.update"), host.update_available ? this._t("upd.available") : this._t("upd.none"));
    if (host.model) add(this._t("field.model"), escapeHtml(host.model));
    add(
      this._t("field.type"),
      escapeHtml(host.device_class_user || host.device_class || "")
    );
    if (host.host_name && host.host_name !== host.name) {
      add(this._t("field.hostname"), escapeHtml(host.host_name));
    }

    const flags = [];
    if (host.guest) flags.push(this._t("badge.guest"));
    if (host.vpn) flags.push(this._t("badge.vpn"));
    if (host.priority) flags.push(this._t("badge.priority"));
    if (host.meshable) flags.push(this._t("badge.mesh"));
    if (flags.length) add(this._t("field.features"), escapeHtml(flags.join(", ")));

    add(
      this._t("field.ha"),
      host.ha_name ? escapeHtml(host.ha_name) : ""
    );

    add(
      this._t("field.last_seen"),
      host.active ? this._t("state.now_online") : escapeHtml(formatLastSeen(host.last_seen, this._lang()))
    );

    // Device Tracker: immer als eigene Zeile - mit dem echten
    // Zustand der Tracker-Entitaet und einem Hinweis, falls es (noch) keinen
    // gibt. Vorher fehlte die Zeile kommentarlos, wenn die Entitaet nicht
    // gefunden wurde - und gefunden wurde bis 1.5.1 nie eine (siehe
    // sensor.py:_trackers_attribute).
    const tracker = this._trackerInfo(host);
    let trackerValue;
    if (tracker.mode === "off") {
      trackerValue = `<span class="fbn-tracker-off" title="${escapeHtml(
        this._t("tracker.off_hint")
      )}">${escapeHtml(this._t("tracker.off"))}</span>`;
    } else if (tracker.mode === "none") {
      trackerValue = "—";
    } else {
      const labels = {
        home: "tracker.home",
        away: "tracker.away",
        disabled: "tracker.disabled",
        unknown: "tracker.unknown",
      };
      const title =
        tracker.mode === "disabled"
          ? this._t("tracker.disabled_hint")
          : this._t("tracker.open");
      trackerValue = `<a class="fbn-tracker-link" href="#" data-entity="${escapeHtml(
        tracker.entity
      )}" title="${escapeHtml(title)}">${escapeHtml(
        this._t(labels[tracker.mode])
      )}</a>`;
    }
    add(this._t("field.tracker"), trackerValue);

    return rows.join("");
  }

  /**
   * Ermittelt Entity und Zustand des Anwesenheits-Trackers eines Geraets.
   *
   * Rueckgabe: { mode, entity }, wobei mode einen der folgenden Faelle
   * beschreibt:
   *   "off"      - Device Tracker in den Integrationseinstellungen aus
   *                (die Integration liefert dann gar keine Zuordnung),
   *   "none"     - Tracker aktiv, aber fuer dieses Geraet keine Entity,
   *   "disabled" - Entity vorhanden, aber ohne Zustand (in Home Assistant
   *                deaktiviert),
   *   "home" / "away" / "unknown" - Zustand der Entity.
   */
  _trackerInfo(host) {
    const state = this._stateObj();
    const trackers =
      state && state.attributes ? state.attributes.trackers : null;
    if (!trackers) return { mode: "off", entity: null };
    const key = String(host.mac || "").replace(/[^a-z0-9]/gi, "").toLowerCase();
    const entity = trackers[key] || null;
    if (!entity) return { mode: "none", entity: null };
    const obj =
      this._hass && this._hass.states ? this._hass.states[entity] : null;
    // Deaktivierte Entitaeten stehen in der Registry (und damit in der
    // Zuordnung), haben aber kein Zustandsobjekt.
    if (!obj) return { mode: "disabled", entity };
    if (obj.state === "home") return { mode: "home", entity };
    if (obj.state === "not_home") return { mode: "away", entity };
    return { mode: "unknown", entity };
  }

  /** Fusszeile des Popups mit den moeglichen Aktionen. */
  _popupButtons(host) {
    const buttons = [];
    const url = this._config.ip_opens_web
      ? webUrl(host, this._config.ip_web_fallback)
      : "";
    if (url) {
      buttons.push(
        `<a class="fbn-btn fbn-act-web" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer"><ha-icon icon="mdi:open-in-new"></ha-icon>${escapeHtml(this._t("btn.web"))}</a>`
      );
    }
    if (host.ha_device_id) {
      buttons.push(
        `<button class="fbn-btn fbn-act-ha" type="button"><ha-icon icon="mdi:open-in-new"></ha-icon>${escapeHtml(this._t("btn.ha"))}</button>`
      );
    }
    // Internetzugang sperren/freigeben - nur mit Home Assistant (Dienstaufruf)
    // und bekannter MAC. Beschriftung richtet sich nach dem aktuellen Zustand.
    if (this._hass && host.mac) {
      const label = host.blocked ? this._t("btn.unblock") : this._t("btn.block");
      const icon = host.blocked ? "mdi:web" : "mdi:web-off";
      buttons.push(
        `<button class="fbn-btn fbn-act-inet" type="button" data-blocked="${
          host.blocked ? "1" : "0"
        }"><ha-icon icon="${icon}"></ha-icon>${escapeHtml(label)}</button>`
      );
    }
    // Aufwecken nur anbieten, wenn das Geraet gerade nicht verbunden ist
    // und Home Assistant fuer den Dienstaufruf bereitsteht.
    if (!host.active && this._hass) {
      buttons.push(
        `<button class="fbn-btn fbn-act-wol" type="button"><ha-icon icon="mdi:power"></ha-icon>${escapeHtml(this._t("btn.wol"))}</button>`
      );
    }
    buttons.push(
      `<button class="fbn-btn fbn-btn-primary fbn-modal-close2" type="button">${escapeHtml(this._t("btn.close"))}</button>`
    );
    return buttons.join("");
  }

  /**
   * Kopiert einen Wert in die Zwischenablage und meldet das Ergebnis mit
   * einer Einblendung von Home Assistant ("hass-notification").
   * Liefert ein Promise<boolean>.
   */
  async _copyValue(value) {
    // Ein offenes Popup ist modal: der Hilfsknoten muss darin liegen, damit
    // der Fokus dort bleibt.
    const ok = await copyToClipboard(value, this._popup || document.body);
    this.dispatchEvent(
      new CustomEvent("hass-notification", {
        detail: { message: ok ? this._t("copy.done", { value }) : this._t("copy.failed") },
        bubbles: true,
        composed: true,
      })
    );
    return ok;
  }

  /** Kopier-Knopf im Popup: Symbol wechselt kurz auf Haken bzw. Kreuz. */
  async _copy(value, button) {
    const ok = await this._copyValue(value);
    const icon = button.querySelector("ha-icon");
    if (!icon) return;
    icon.setAttribute("icon", ok ? "mdi:check" : "mdi:close");
    setTimeout(() => icon.setAttribute("icon", "mdi:content-copy"), 1200);
  }

  /** Klick auf eine MAC-Adresse in der Tabelle: kopieren, kurz markieren. */
  async _copyFromCell(cell) {
    const ok = await this._copyValue(cell.dataset.copy || "");
    const cls = ok ? "fbn-copy-ok" : "fbn-copy-fail";
    cell.classList.add(cls);
    setTimeout(() => cell.classList.remove(cls), 1200);
  }

  /** Ruft den Wake-on-LAN-Dienst der Integration auf. */
  _wakeDevice(host, button) {
    if (!this._hass || !host.mac) return;
    button.disabled = true;
    const label = button;
    this._hass
      .callService("fritzbox_netzwerk", "wake_on_lan", { mac: host.mac })
      .then(() => {
        label.innerHTML = `<ha-icon icon="mdi:check"></ha-icon>${escapeHtml(this._t("act.wol_sent"))}`;
      })
      .catch(() => {
        label.disabled = false;
        label.innerHTML = `<ha-icon icon="mdi:alert"></ha-icon>${escapeHtml(this._t("act.failed"))}`;
      });
  }

  /** Ruft den Internet-Sperr-Dienst auf und dreht den Zustand um. */
  _setInternet(host, button) {
    if (!this._hass || !host.mac) return;
    const willBlock = button.dataset.blocked !== "1";
    button.disabled = true;
    button.innerHTML =
      '<ha-icon icon="mdi:progress-clock"></ha-icon>' +
      escapeHtml(willBlock ? this._t("act.blocking") : this._t("act.unblocking"));
    this._hass
      .callService("fritzbox_netzwerk", "set_internet_access", {
        mac: host.mac,
        blocked: willBlock,
      })
      .then(() => {
        button.innerHTML =
          '<ha-icon icon="mdi:check"></ha-icon>' +
          escapeHtml(willBlock ? this._t("act.blocked") : this._t("act.unblocked"));
        // Der Coordinator aktualisiert danach; beim nächsten Datenupdate
        // baut _refreshPopup() den Knopf mit dem neuen Zustand neu.
      })
      .catch(() => {
        button.disabled = false;
        button.innerHTML = `<ha-icon icon="mdi:alert"></ha-icon>${escapeHtml(this._t("act.failed"))}`;
      });
  }

  /** Schliesst das Popup und raeumt Listener und Fokus auf. */
  _closePopup() {
    if (!this._popup) return;
    if (this._onPopupKeydown) {
      this._popup.removeEventListener("keydown", this._onPopupKeydown);
      this._onPopupKeydown = null;
    }
    if (this._popup.parentNode) this._popup.parentNode.removeChild(this._popup);
    this._popup = null;
    this._popupMac = null;
    this._parental = null;
    this._popupEditingName = false;
    this._popupNameDraft = "";
    const returnTo = this._popupReturnFocus;
    this._popupReturnFocus = null;
    if (returnTo && returnTo.focus && document.contains(returnTo)) {
      returnTo.focus();
    }
  }

  /* -- Gast-WLAN-Popup (Idee 11) -------------------------------------
   *
   * Eigenstaendiges Popup fuer SSID, Passwort und QR-Code des Gast-WLANs -
   * unabhaengig vom Geraete-Detail-Popup oben (eigener Overlay-Knoten,
   * eigener Zustand ``_gastWlanPopup``), weil es sich nicht auf ein
   * bestimmtes Geraet bezieht. Die Zugangsdaten kommen AUSSCHLIESSLICH aus
   * der Rueckgabe des Dienstes fritzbox_netzwerk.gast_wlan_info
   * (SupportsResponse.ONLY) - nie aus einem Sensor-Attribut, siehe
   * __init__.py. Sie werden hier nirgends zwischengespeichert und
   * verschwinden mit dem Schliessen des Popups wieder.
   */

  /** Oeffnet das Gast-WLAN-Popup und stoesst das Laden der Daten an. */
  _openGastWlanPopup() {
    if (!this._hass) return;
    this._closeGastWlanPopup();

    const overlay = document.createElement("div");
    overlay.className = "fbn-overlay";
    overlay.innerHTML = `
      <style>${this._popupStyles()}</style>
      <div class="fbn-modal" role="dialog" aria-modal="true"
           aria-label="${escapeHtml(this._t("gwlan.title"))}">
        <div class="fbn-modal-head">
          <ha-icon class="fbn-modal-icon" icon="mdi:qrcode"></ha-icon>
          <div class="fbn-modal-titles">
            <div class="fbn-modal-title">${escapeHtml(this._t("gwlan.title"))}</div>
            <div class="fbn-modal-sub"></div>
          </div>
          <button class="fbn-modal-close" type="button" aria-label="${escapeHtml(this._t('btn.close'))}">
            <ha-icon icon="mdi:close"></ha-icon>
          </button>
        </div>
        <div class="fbn-modal-body">
          <div class="fbn-gwlan-loading">${escapeHtml(this._t("gwlan.loading"))}</div>
        </div>
        <div class="fbn-modal-foot">
          <button class="fbn-btn fbn-btn-primary fbn-modal-close2" type="button">${escapeHtml(
            this._t("btn.close")
          )}</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    this._gastWlanPopup = overlay;

    overlay.addEventListener("mousedown", (event) => {
      if (event.target === overlay) this._closeGastWlanPopup();
    });
    this._onGastWlanKeydown = (event) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        this._closeGastWlanPopup();
      }
    };
    overlay.addEventListener("keydown", this._onGastWlanKeydown);
    overlay
      .querySelector(".fbn-modal-close")
      .addEventListener("click", () => this._closeGastWlanPopup());
    overlay
      .querySelector(".fbn-modal-close2")
      .addEventListener("click", () => this._closeGastWlanPopup());

    const close = overlay.querySelector(".fbn-modal-close");
    if (close && close.focus) close.focus();

    this._fetchGastWlanInfo();
  }

  /** Ruft gast_wlan_info auf und baut den Popup-Inhalt mit dem Ergebnis neu auf. */
  _fetchGastWlanInfo() {
    this._hass
      .callService("fritzbox_netzwerk", "gast_wlan_info", {}, undefined, true, true)
      .then((result) => {
        if (!this._gastWlanPopup) return;
        this._renderGastWlanPopupContent((result && result.response) || {});
      })
      .catch((err) => {
        if (!this._gastWlanPopup) return;
        this._renderGastWlanPopupError(err);
      });
  }

  /** Baut den Popup-Inhalt (SSID, Passwort, QR-Code) aus der Dienst-Antwort. */
  _renderGastWlanPopupContent(data) {
    const body = this._gastWlanPopup.querySelector(".fbn-modal-body");
    if (!body) return;

    const rows = [];
    const add = (label, valueHtml, copyValue) => {
      const copy =
        copyValue
          ? `<button class="fbn-copy" type="button" data-copy="${escapeHtml(
              copyValue
            )}" aria-label="${escapeHtml(
              this._t("copy.aria", { label })
            )}"><ha-icon icon="mdi:content-copy"></ha-icon></button>`
          : "";
      rows.push(`
        <div class="fbn-drow">
          <div class="fbn-dt">${escapeHtml(label)}</div>
          <div class="fbn-dd">${valueHtml}${copy}</div>
        </div>`);
    };

    const qr = data.qr_code_svg_base64
      ? `<div class="fbn-gwlan-qr"><img alt="${escapeHtml(
          this._t("gwlan.title")
        )}" src="data:image/svg+xml;base64,${data.qr_code_svg_base64}"></div>`
      : "";

    add(this._t("gwlan.ssid"), escapeHtml(data.ssid || ""), data.ssid || "");
    if (data.offen) {
      add(this._t("gwlan.password"), escapeHtml(this._t("gwlan.open_network")));
    } else if (data.passwort) {
      add(this._t("gwlan.password"), escapeHtml(data.passwort), data.passwort);
    }

    const hint =
      data.eingeschaltet === false
        ? `<div class="fbn-modal-note">${escapeHtml(this._t("gwlan.disabled_hint"))}</div>`
        : `<div class="fbn-modal-note">${escapeHtml(this._t("gwlan.scan_hint"))}</div>`;

    body.innerHTML = `${qr}${rows.join("")}${hint}`;
    body.querySelectorAll(".fbn-copy").forEach((button) => {
      button.addEventListener("click", () => this._copy(button.dataset.copy, button));
    });
  }

  /** Zeigt eine Fehlermeldung im Gast-WLAN-Popup (z. B. kein Gast-WLAN). */
  _renderGastWlanPopupError(err) {
    const body = this._gastWlanPopup.querySelector(".fbn-modal-body");
    if (!body) return;
    const message = (err && err.message) || String(err || "");
    body.innerHTML = `<div class="fbn-modal-note fbn-gwlan-error">${escapeHtml(
      this._t("gwlan.error", { error: message })
    )}</div>`;
  }

  /** Schliesst das Gast-WLAN-Popup und raeumt Listener/Fokus auf. */
  _closeGastWlanPopup() {
    if (!this._gastWlanPopup) return;
    if (this._onGastWlanKeydown) {
      this._gastWlanPopup.removeEventListener("keydown", this._onGastWlanKeydown);
      this._onGastWlanKeydown = null;
    }
    if (this._gastWlanPopup.parentNode) {
      this._gastWlanPopup.parentNode.removeChild(this._gastWlanPopup);
    }
    this._gastWlanPopup = null;
  }

  /* -- Breite ------------------------------------------------------- */

  /**
   * Aktualisiert die Blätter-Pfeile, wenn sich die Kartenbreite aendert.
   * Spalten werden bewusst NICHT mehr versteckt - auf schmalen Karten
   * wird die Tabelle stattdessen waagerecht scrollbar, damit auch die
   * hinteren Spalten (z. B. Home Assistant) erreichbar bleiben.
   */
  _observeWidth() {
    if (this._resizeObserver || typeof ResizeObserver === "undefined") return;
    if (!this._root) return;
    this._resizeObserver = new ResizeObserver(() => {
      this._updateArrows();
      this._applyMaxRows();
    });
    this._resizeObserver.observe(this._root);
  }

  /* -- Farben und CSS ----------------------------------------------- */

  /** Baut die Inline-CSS-Variablen aus den konfigurierten Farben. */
  _colorVars() {
    return Object.keys(COLOR_FALLBACKS)
      .map((key) => {
        const value = sanitizeColor(this._config[key]);
        const variable = `--fbn-${key.replace("color_", "").replace(/_/g, "-")}`;
        return `${variable}: ${value || COLOR_FALLBACKS[key]};`;
      })
      .join("");
  }

  _styles() {
    return `
      .fbn-root { padding: 0 0 8px; color: var(--fbn-row-text); }
      /* Das hidden-Attribut muss staerker sein als die display-Regeln
         weiter unten (.fbn-toolbar/.fbn-controls/... setzen display:flex,
         was die Browser-Regel [hidden]{display:none} ueberstimmt). Ohne
         diese Zeile blieben Filter/Suche und die Steuerungsleiste beim
         Umschalten der Kategorien in BEIDEN Reitern sichtbar. */
      .fbn-root [hidden] { display: none !important; }
      .fbn-tabbar {
        display: flex; gap: 4px; padding: 8px 16px 4px; flex-wrap: wrap;
      }
      .fbn-tab {
        display: inline-flex; align-items: center; gap: 6px;
        border: none; border-bottom: 2px solid transparent; background: none;
        color: var(--fbn-header-text); cursor: pointer; font: inherit;
        font-size: 0.9em; padding: 6px 12px 8px;
      }
      .fbn-tab ha-icon { --mdc-icon-size: 18px; width: 18px; height: 18px; }
      .fbn-tab[aria-selected="true"] {
        color: var(--fbn-accent); border-bottom-color: var(--fbn-accent);
      }
      .fbn-tab:focus-visible { outline: 2px solid var(--fbn-accent); outline-offset: 2px; }
      .fbn-tracker-link { color: var(--fbn-accent); text-decoration: none; }
      .fbn-tracker-off { opacity: 0.7; cursor: help; }
      .fbn-tracker-link:hover { text-decoration: underline; }
      .fbn-toolbar {
        display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
        justify-content: space-between; padding: 8px 16px 4px;
      }
      .fbn-filters { display: flex; flex-wrap: wrap; gap: 6px; }
      .fbn-chip {
        display: inline-flex; align-items: center; gap: 4px;
        border: 1px solid var(--fbn-border); border-radius: 16px;
        background: none; color: inherit; cursor: pointer;
        padding: 4px 10px; font: inherit; font-size: 0.85em; line-height: 1.4;
      }
      .fbn-chip ha-icon { --mdc-icon-size: 16px; width: 16px; height: 16px; }
      .fbn-chip[aria-pressed="true"] {
        border-color: var(--fbn-accent); color: var(--fbn-accent);
      }
      .fbn-chip:focus-visible { outline: 2px solid var(--fbn-accent); outline-offset: 2px; }
      .fbn-search {
        display: inline-flex; align-items: center; gap: 6px;
        border: 1px solid var(--fbn-border); border-radius: 16px; padding: 3px 10px;
      }
      .fbn-search ha-icon { --mdc-icon-size: 18px; width: 18px; height: 18px; opacity: 0.7; }
      .fbn-search input {
        border: none; background: none; color: inherit; font: inherit;
        font-size: 0.9em; min-width: 120px; padding: 2px 0; outline: none;
      }
      .fbn-tools { display: inline-flex; align-items: center; gap: 8px; flex-wrap: wrap; }
      .fbn-tools[hidden] { display: none; }
      .fbn-group-select {
        display: inline-flex; align-items: center; gap: 5px;
        border: 1px solid var(--fbn-border); border-radius: 16px; padding: 2px 8px;
        font-size: 0.85em;
      }
      .fbn-group-select ha-icon { --mdc-icon-size: 16px; width: 16px; height: 16px; opacity: 0.7; }
      .fbn-group-select select {
        border: none; background: none; color: inherit; font: inherit; outline: none;
        cursor: pointer; max-width: 160px;
      }
      .fbn-group-select select option { color: initial; }
      .fbn-group-row { cursor: pointer; }
      .fbn-group-cell {
        padding: 6px 10px; font-weight: 600; font-size: 0.9em;
        background: var(--fbn-row-alt, rgba(127,127,127,0.12));
        border-bottom: 1px solid var(--fbn-border);
      }
      .fbn-group-cell ha-icon { --mdc-icon-size: 18px; width: 18px; height: 18px; vertical-align: middle; }
      .fbn-group-count {
        margin-left: 6px; font-weight: 400; opacity: 0.7;
        border: 1px solid var(--fbn-border); border-radius: 10px; padding: 0 7px; font-size: 0.85em;
      }
      .fbn-group-row:focus-visible { outline: 2px solid var(--fbn-accent); outline-offset: -2px; }
      .fbn-label-chip {
        display: inline-block; border: 1px solid var(--fbn-border); border-radius: 10px;
        padding: 0 8px; font-size: 0.85em; background: var(--fbn-row-alt, rgba(127,127,127,0.1));
      }
      .fbn-note-text { opacity: 0.85; }
      .fbn-copywrap[hidden] { display: none; }
      .fbn-copy-list {
        display: inline-flex; align-items: center; gap: 5px;
        border: 1px solid var(--fbn-border); border-radius: 16px;
        background: none; color: inherit; cursor: pointer;
        padding: 4px 12px; font: inherit; font-size: 0.85em; line-height: 1.4;
      }
      .fbn-copy-list ha-icon { --mdc-icon-size: 16px; width: 16px; height: 16px; }
      .fbn-copy-list:hover { color: var(--primary-color, #03a9f4); }
      .fbn-copy-list:focus-visible { outline: 2px solid var(--fbn-accent); outline-offset: 2px; }
      .fbn-copy-list.fbn-copy-ok { border-color: var(--fbn-active); color: var(--fbn-active); }
      .fbn-copy-list.fbn-copy-fail { border-color: var(--fbn-blocked); color: var(--fbn-blocked); }
      .fbn-summary {
        padding: 2px 16px 8px; font-size: 0.82em; color: var(--fbn-header-text);
      }
      .fbn-controls {
        display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
        padding: 4px 16px 10px;
      }
      .fbn-ctl-rate {
        display: inline-flex; align-items: center; gap: 4px;
        font-size: 0.85em; color: var(--fbn-header-text);
      }
      .fbn-ctl-rate ha-icon { --mdc-icon-size: 16px; width: 16px; height: 16px; }
      .fbn-ctl-verbox {
        display: inline-flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-left: auto;
      }
      .fbn-ctl-version {
        display: inline-flex; align-items: center; gap: 4px;
        font-size: 0.8em; color: var(--fbn-header-text); opacity: 0.85;
      }
      .fbn-ctl-version ha-icon, .fbn-ctl-update ha-icon { --mdc-icon-size: 15px; width: 15px; height: 15px; }
      .fbn-ctl-update {
        display: inline-flex; align-items: center; gap: 4px; text-decoration: none;
        font-size: 0.8em; font-weight: 600; line-height: 1.4; padding: 2px 10px; border-radius: 12px;
        background: var(--fbn-update-bg, var(--warning-color, #ff9800)); color: #fff;
      }
      a.fbn-ctl-update:hover { filter: brightness(1.1); }
      a.fbn-ctl-update:focus-visible { outline: 2px solid var(--fbn-accent); outline-offset: 2px; }
      .fbn-ctl-mismatch { background: var(--error-color, #db4437); font-weight: 500; }
      .fbn-ctl-chip, .fbn-ctl-btn {
        display: inline-flex; align-items: center; gap: 5px;
        border: 1px solid var(--fbn-border); border-radius: 16px;
        background: none; color: inherit; cursor: pointer;
        padding: 4px 12px; font: inherit; font-size: 0.85em; line-height: 1.4;
      }
      .fbn-ctl-chip ha-icon, .fbn-ctl-btn ha-icon {
        --mdc-icon-size: 16px; width: 16px; height: 16px;
      }
      .fbn-ctl-wlan[aria-pressed="true"], .fbn-ctl-mac[aria-pressed="true"] {
        border-color: var(--fbn-active); color: var(--fbn-active);
      }
      .fbn-ctl-wlan[aria-pressed="false"], .fbn-ctl-mac[aria-pressed="false"]:not(.fbn-ctl-armed) { opacity: 0.6; }
      .fbn-ctl-btn:hover, .fbn-ctl-chip:hover { background: var(--fbn-header-bg); }
      .fbn-ctl-btn[disabled] { opacity: 0.6; cursor: default; }
      .fbn-ctl-armed {
        border-color: var(--fbn-blocked); color: var(--fbn-blocked);
        font-weight: 600;
      }
      .fbn-mesh {
        flex: 1 1 100%; display: flex; flex-wrap: wrap; align-items: center;
        gap: 6px 10px; border: 1px solid var(--fbn-border); border-radius: 12px;
        padding: 6px 12px;
      }
      .fbn-mesh-incomplete { border-color: var(--fbn-blocked); }
      .fbn-mesh-title {
        display: inline-flex; align-items: center; gap: 5px; font-size: 0.85em;
      }
      .fbn-mesh-title ha-icon { --mdc-icon-size: 18px; width: 18px; height: 18px; }
      .fbn-mesh-title > span { color: var(--fbn-header-text); }
      .fbn-mesh-members { display: inline-flex; flex-wrap: wrap; gap: 4px 12px; flex: 1 1 auto; }
      .fbn-mesh-member {
        display: inline-flex; align-items: center; gap: 4px; font-size: 0.85em;
      }
      .fbn-mesh-member ha-icon { --mdc-icon-size: 16px; width: 16px; height: 16px; }
      .fbn-mesh-on ha-icon { color: var(--fbn-active); }
      .fbn-mesh-off { opacity: 0.6; }
      .fbn-mesh-off ha-icon { color: var(--fbn-blocked); }
      .fbn-ctl-chip:focus-visible, .fbn-ctl-btn:focus-visible {
        outline: 2px solid var(--fbn-accent); outline-offset: 2px;
      }
      .fbn-scrollwrap { position: relative; }
      .fbn-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
      .fbn-arrow {
        position: absolute; top: 0; bottom: 0; width: 34px; z-index: 5;
        border: none; cursor: pointer; display: flex; align-items: center;
        justify-content: center; color: var(--fbn-accent);
        background: linear-gradient(
          to var(--fbn-arrow-dir, right),
          var(--card-background-color, rgba(255,255,255,0.96)),
          rgba(0, 0, 0, 0)
        );
      }
      .fbn-arrow[hidden] { display: none; }
      .fbn-arrow ha-icon { --mdc-icon-size: 26px; width: 26px; height: 26px;
        background: var(--card-background-color, #fff); border-radius: 50%;
        box-shadow: 0 1px 4px rgba(0,0,0,0.25); }
      .fbn-arrow-left { left: 0; --fbn-arrow-dir: right; }
      .fbn-arrow-right { right: 0; --fbn-arrow-dir: left; }
      .fbn-arrow:focus-visible { outline: 2px solid var(--fbn-accent); outline-offset: -2px; }
      .fbn-table { width: 100%; border-collapse: collapse; font-size: 0.92em; }
      .fbn-th {
        position: sticky; top: 0; z-index: 1;
        background: var(--fbn-header-bg); color: var(--fbn-header-text);
        font-weight: 500; font-size: 0.85em; white-space: nowrap;
        padding: 8px 12px; cursor: pointer; user-select: none;
        border-bottom: 1px solid var(--fbn-border);
      }
      .fbn-th-inner { display: inline-flex; align-items: center; gap: 4px; }
      .fbn-th.fbn-sorted { color: var(--fbn-accent); }
      .fbn-sorticon { --mdc-icon-size: 14px; width: 14px; height: 14px; }
      .fbn-td {
        padding: 8px 12px; border-bottom: 1px solid var(--fbn-border);
        vertical-align: middle;
      }
      .fbn-compact .fbn-td, .fbn-compact .fbn-th { padding: 4px 8px; }
      .fbn-tr:nth-child(even) { background: var(--fbn-row-alt-bg); }
      .fbn-tr:last-child .fbn-td { border-bottom: none; }
      .fbn-inactive { opacity: 0.55; }
      .fbn-clickable { cursor: pointer; }
      .fbn-clickable:hover { background: var(--fbn-header-bg); }
      /* Sticky: Status und Gerätename bleiben beim Blättern links stehen. */
      .fbn-sticky .fbn-col-status {
        position: sticky; left: 0; z-index: 2; box-sizing: border-box;
        width: 40px; min-width: 40px;
        background: var(--card-background-color, #fff);
      }
      .fbn-sticky .fbn-col-name {
        position: sticky; left: 40px; z-index: 2; box-sizing: border-box;
        background: var(--card-background-color, #fff);
      }
      .fbn-sticky .fbn-th.fbn-col-status,
      .fbn-sticky .fbn-th.fbn-col-name {
        z-index: 3; background: var(--fbn-header-bg);
      }
      .fbn-namecell { display: flex; align-items: center; gap: 6px; min-width: 0; }
      .fbn-rowicon { --mdc-icon-size: 18px; width: 18px; height: 18px; flex: 0 0 auto; }
      .fbn-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        max-width: 40vw; }
      .fbn-mono { font-family: var(--code-font-family, monospace); font-size: 0.95em; }
      .fbn-maccopy { cursor: copy; border-bottom: 1px dotted currentColor; }
      .fbn-maccopy:hover { color: var(--fbn-accent); }
      .fbn-maccopy:focus-visible { outline: 2px solid var(--fbn-accent); outline-offset: 1px; }
      .fbn-maccopy.fbn-copy-ok { color: var(--fbn-active); }
      .fbn-maccopy.fbn-copy-ok::after { content: " \\2713"; }
      .fbn-maccopy.fbn-copy-fail { color: var(--fbn-blocked); }
      .fbn-maccopy.fbn-copy-fail::after { content: " \\2715"; }
      .fbn-iplink {
        color: var(--fbn-accent); text-decoration: none;
        display: inline-flex; align-items: center; gap: 3px;
      }
      .fbn-iplink:hover { text-decoration: underline; }
      .fbn-iplink-icon {
        --mdc-icon-size: 13px; width: 13px; height: 13px; opacity: 0;
        transition: opacity 120ms ease;
      }
      .fbn-iplink:hover .fbn-iplink-icon,
      .fbn-iplink:focus-visible .fbn-iplink-icon { opacity: 0.7; }
      .fbn-halink { color: var(--fbn-accent); text-decoration: none; }
      .fbn-halink:hover { text-decoration: underline; }
      .fbn-halink:focus-visible { outline: 2px solid var(--fbn-accent); outline-offset: 2px; border-radius: 2px; }
      .fbn-dim { color: var(--fbn-inactive); }
      .fbn-ls-now { color: var(--fbn-active); }
      .fbn-lease { font-size: 0.85em; }
      .fbn-dot {
        display: inline-block; width: 10px; height: 10px; border-radius: 50%;
      }
      .fbn-dot-on { background: var(--fbn-active); }
      .fbn-dot-off { background: var(--fbn-inactive); }
      .fbn-badge {
        display: inline-block; border-radius: 4px; padding: 1px 6px;
        font-size: 0.72em; border: 1px solid var(--fbn-border); white-space: nowrap;
      }
      .fbn-badge-guest { color: var(--fbn-guest); border-color: var(--fbn-guest); }
      .fbn-badge-static { color: var(--fbn-static); border-color: var(--fbn-static); }
      .fbn-icon-blocked { color: var(--fbn-blocked); --mdc-icon-size: 18px; width: 18px; height: 18px; }
      .fbn-icon-update { color: var(--fbn-update); --mdc-icon-size: 18px; width: 18px; height: 18px; }
      .fbn-empty { padding: 16px; text-align: center; color: var(--fbn-inactive); }
      .fbn-clickable:focus-visible { outline: 2px solid var(--fbn-accent); outline-offset: -2px; }
      @media (prefers-reduced-motion: no-preference) {
        .fbn-chip, .fbn-tr { transition: color 120ms ease, background 120ms ease; }
      }
    `;
  }

  /**
   * Styles des Detail-Popups. Getrennt von _styles(), weil der Overlay-
   * Knoten am document.body haengt und dort sein eigenes <style> braucht.
   */
  _popupStyles() {
    return `
      .fbn-overlay {
        position: fixed; inset: 0; z-index: 9999;
        background: rgba(0, 0, 0, 0.45);
        display: flex; align-items: center; justify-content: center;
        padding: 16px;
      }
      .fbn-modal {
        background: var(--card-background-color, var(--ha-card-background, #fff));
        color: var(--primary-text-color, #212121);
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
        width: min(460px, 100%); max-height: min(80vh, 640px);
        display: flex; flex-direction: column; overflow: hidden;
        font-family: var(--primary-font-family, inherit);
      }
      .fbn-modal-head {
        display: flex; align-items: center; gap: 12px;
        padding: 16px 16px 12px; border-bottom: 1px solid var(--divider-color, #e0e0e0);
      }
      .fbn-modal-icon { --mdc-icon-size: 26px; width: 26px; height: 26px; flex: 0 0 auto; }
      .fbn-modal-titles { flex: 1; min-width: 0; }
      .fbn-modal-title {
        font-size: 1.15em; font-weight: 500;
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
      }
      .fbn-modal-sub {
        font-size: 0.82em; color: var(--secondary-text-color, #727272);
        display: flex; align-items: center; gap: 6px; margin-top: 2px;
      }
      .fbn-modal-close {
        border: none; background: none; cursor: pointer; padding: 4px;
        color: var(--secondary-text-color, #727272); border-radius: 50%;
        display: inline-flex; flex: 0 0 auto;
      }
      .fbn-modal-close:hover { background: var(--divider-color, #e0e0e0); }
      .fbn-modal-body { padding: 8px 16px; overflow-y: auto; }
      .fbn-modal-note {
        background: var(--warning-color, #ffa600); color: #000;
        border-radius: 6px; padding: 6px 10px; margin: 8px 0; font-size: 0.85em;
      }
      .fbn-gwlan-loading {
        padding: 24px 0; text-align: center; color: var(--secondary-text-color, #727272);
      }
      .fbn-gwlan-error {
        background: var(--error-color, #db4437); color: #fff;
      }
      .fbn-gwlan-qr {
        display: flex; justify-content: center; padding: 8px 0 16px;
      }
      .fbn-gwlan-qr img {
        width: 200px; height: 200px; background: #fff; padding: 8px;
        border-radius: 8px; box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
      }
      .fbn-drow {
        display: flex; justify-content: space-between; gap: 16px;
        padding: 7px 0; border-bottom: 1px solid var(--divider-color, #ededed);
      }
      .fbn-drow:last-child { border-bottom: none; }
      .fbn-dt { color: var(--secondary-text-color, #727272); font-size: 0.9em; flex: 0 0 auto; }
      .fbn-dd {
        text-align: right; word-break: break-word;
        display: inline-flex; align-items: center; gap: 6px; justify-content: flex-end;
      }
      .fbn-dd.fbn-mono { font-family: var(--code-font-family, monospace); }
      .fbn-copy {
        border: none; background: none; cursor: pointer; padding: 2px;
        color: var(--secondary-text-color, #727272); display: inline-flex;
        border-radius: 4px;
      }
      .fbn-copy:hover { color: var(--primary-color, #03a9f4); }
      .fbn-copy ha-icon { --mdc-icon-size: 16px; width: 16px; height: 16px; }
      .fbn-namebtn {
        border: none; background: none; cursor: pointer; padding: 2px;
        color: var(--secondary-text-color, #727272); display: inline-flex;
        border-radius: 4px; flex: 0 0 auto;
      }
      .fbn-namebtn:hover { color: var(--primary-color, #03a9f4); }
      .fbn-namebtn ha-icon { --mdc-icon-size: 16px; width: 16px; height: 16px; }
      .fbn-namebtn[disabled] { opacity: 0.5; cursor: default; }
      .fbn-name-save { color: var(--success-color, #43a047); }
      .fbn-name-save:hover { color: var(--success-color, #43a047); }
      .fbn-name-cancel { color: var(--error-color, #db4437); }
      .fbn-name-cancel:hover { color: var(--error-color, #db4437); }
      .fbn-name-saved { color: var(--success-color, #43a047); cursor: default; }
      .fbn-name-edit {
        display: inline-flex; align-items: center; gap: 2px;
        flex: 1 1 auto; min-width: 0; justify-content: flex-end;
      }
      .fbn-name-input {
        flex: 1 1 auto; min-width: 0; max-width: 200px;
        border: 1px solid var(--divider-color, #e0e0e0); border-radius: 6px;
        background: var(--card-background-color, var(--ha-card-background, #fff));
        color: inherit; font: inherit; font-size: 0.95em; padding: 3px 6px;
      }
      .fbn-name-input[disabled] { opacity: 0.6; }
      .fbn-note-full { white-space: pre-wrap; word-break: break-word; }
      .fbn-label-chip {
        display: inline-block; border: 1px solid var(--divider-color, #e0e0e0); border-radius: 10px;
        padding: 0 8px; font-size: 0.9em;
      }
      .fbn-note-fields { display: flex; flex-direction: column; gap: 6px; align-items: stretch; flex: 1 1 auto; min-width: 0; }
      .fbn-note-fields input[type="text"], .fbn-note-fields textarea {
        border: 1px solid var(--divider-color, #e0e0e0); border-radius: 6px;
        background: var(--card-background-color, var(--ha-card-background, #fff));
        color: inherit; font: inherit; font-size: 0.95em; padding: 4px 6px;
        width: 100%; box-sizing: border-box; resize: vertical;
      }
      .fbn-note-reserved { display: flex; gap: 6px; align-items: center; font-size: 0.9em; }
      .fbn-note-hint { font-size: 0.8em; opacity: 0.7; }
      .fbn-prof-box { display: flex; flex-direction: column; gap: 6px; align-items: flex-start; }
      .fbn-prof-line { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
      .fbn-prof-select, .fbn-prof-minutes {
        font: inherit; color: inherit; background: var(--fbn-bg, transparent);
        border: 1px solid var(--fbn-border); border-radius: 6px; padding: 4px 8px; max-width: 100%;
      }
      .fbn-prof-minutes { width: 9em; }
      .fbn-prof-btn {
        display: inline-flex; align-items: center; gap: 4px; font: inherit; font-size: 0.9em;
        cursor: pointer; color: inherit; background: none; border: 1px solid var(--fbn-border);
        border-radius: 14px; padding: 3px 12px;
      }
      .fbn-prof-btn[disabled] { opacity: 0.5; cursor: default; }
      .fbn-prof-err { color: var(--fbn-blocked); font-size: 0.85em; }
      .fbn-prof-hint { font-size: 0.8em; opacity: 0.7; }
      .fbn-note-actions { display: flex; gap: 4px; justify-content: flex-end; }
      .fbn-note-form input[disabled], .fbn-note-form textarea[disabled] { opacity: 0.6; }
      .fbn-modal-foot {
        display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end;
        padding: 12px 16px 16px; border-top: 1px solid var(--divider-color, #e0e0e0);
      }
      .fbn-btn {
        display: inline-flex; align-items: center; gap: 6px;
        border: 1px solid var(--divider-color, #e0e0e0); border-radius: 8px;
        background: none; color: inherit; font: inherit; font-size: 0.9em;
        padding: 8px 14px; cursor: pointer;
      }
      .fbn-btn ha-icon { --mdc-icon-size: 18px; width: 18px; height: 18px; }
      a.fbn-btn { text-decoration: none; color: inherit; }
      .fbn-btn:hover { background: var(--divider-color, #f0f0f0); }
      .fbn-btn[disabled] { opacity: 0.6; cursor: default; }
      .fbn-btn-primary {
        border-color: var(--primary-color, #03a9f4); color: var(--primary-color, #03a9f4);
      }
      .fbn-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; }
      .fbn-dot-on { background: var(--success-color, #43a047); }
      .fbn-dot-off { background: var(--disabled-text-color, #9e9e9e); }
    `;
  }
}

/* ------------------------------------------------------------------ */
/* Editor                                                              */
/* ------------------------------------------------------------------ */

const EDITOR_SCHEMA = [
  { name: "entity", required: true, selector: { entity: { domain: "sensor" } } },
  { name: "title", selector: { text: {} } },
  { name: "show_title", selector: { boolean: {} } },
  { name: "ip_filter", selector: { text: {} } },
  {
    name: "language",
    selector: {
      select: {
        mode: "dropdown",
        options: [
          { value: "", label: "Automatisch (Home Assistant)" },
          { value: "de", label: "Deutsch" },
          { value: "en", label: "English" },
          { value: "nl", label: "Nederlands" },
        ],
      },
    },
  },
  {
    type: "expandable",
    name: "spalten",
    title: "Spalten",
    flatten: true,
    icon: "mdi:table-column",
    schema: COLUMNS.map((column) => ({
      name: column.cfg,
      selector: { boolean: {} },
    })),
  },
  {
    type: "expandable",
    name: "darstellung",
    title: "Darstellung",
    flatten: true,
    icon: "mdi:tune",
    schema: [
      { name: "show_summary", selector: { boolean: {} } },
      { name: "show_search", selector: { boolean: {} } },
      { name: "show_filter", selector: { boolean: {} } },
      { name: "show_controls", selector: { boolean: {} } },
      { name: "show_version", selector: { boolean: {} } },
      { name: "show_parental", selector: { boolean: {} } },
      { name: "show_tabs", selector: { boolean: {} } },
      {
        name: "group_by",
        selector: {
          select: {
            mode: "dropdown",
            options: [{ value: "", label: "Nicht gruppieren" }].concat(
              GROUP_MODES.map((mode) => ({ value: mode, label: mode }))
            ),
          },
        },
      },
      { name: "show_group_select", selector: { boolean: {} } },
      { name: "show_csv_export", selector: { boolean: {} } },
      { name: "remember_view", selector: { boolean: {} } },
      { name: "hide_inactive", selector: { boolean: {} } },
      { name: "compact", selector: { boolean: {} } },
      { name: "mac_click_copies", selector: { boolean: {} } },
      { name: "show_details_popup", selector: { boolean: {} } },
      { name: "open_device_on_click", selector: { boolean: {} } },
      { name: "show_scroll_arrows", selector: { boolean: {} } },
      { name: "sticky_name", selector: { boolean: {} } },
      { name: "ip_opens_web", selector: { boolean: {} } },
      { name: "ip_web_fallback", selector: { boolean: {} } },
      {
        name: "max_rows",
        selector: { number: { min: 0, max: 500, mode: "box" } },
      },
      {
        name: "max_visible_rows",
        selector: { number: { min: 0, max: 100, mode: "box" } },
      },
    ],
  },
  {
    type: "expandable",
    name: "filter_buttons",
    title: "Filter-Buttons",
    flatten: true,
    icon: "mdi:filter-variant",
    schema: [
      { name: "filter_alle", selector: { boolean: {} } },
      { name: "filter_aktiv", selector: { boolean: {} } },
      { name: "filter_inaktiv", selector: { boolean: {} } },
      { name: "filter_gast", selector: { boolean: {} } },
      { name: "filter_gesperrt", selector: { boolean: {} } },
      { name: "filter_update", selector: { boolean: {} } },
      { name: "filter_fest", selector: { boolean: {} } },
      { name: "filter_neu", selector: { boolean: {} } },
      { name: "filter_lange_offline", selector: { boolean: {} } },
      {
        name: "default_filter",
        selector: {
          select: {
            mode: "dropdown",
            options: FILTERS.map((filter) => ({ value: filter.key, label: filter.label })),
          },
        },
      },
    ],
  },
  {
    type: "expandable",
    name: "sortierung",
    title: "Sortierung",
    flatten: true,
    icon: "mdi:sort",
    schema: [
      {
        name: "sort_by",
        selector: {
          select: {
            mode: "dropdown",
            options: COLUMNS.map((column) => ({
              value: column.key,
              label: column.key === "status" ? "Status" : column.label,
            })),
          },
        },
      },
      {
        name: "sort_dir",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "asc", label: "Aufsteigend" },
              { value: "desc", label: "Absteigend" },
            ],
          },
        },
      },
    ],
  },
];

const EDITOR_LABELS = {
  entity: "Sensor mit der Geräteliste",
  title: "Titel",
  show_title: "Titel anzeigen",
  ip_filter: "IP-Filter (Platzhalter erlaubt)",
  language: "Sprache der Karte",
  show_status: "Status",
  show_name: "Gerät",
  show_ip: "IP-Adresse",
  show_mac: "MAC-Adresse",
  show_connection: "Verbindung",
  show_ha_name: "Home-Assistant-Gerätename (verlinkt)",
  show_ip_type: "IP-Typ (DHCP oder statisch)",
  show_wan: "Internetzugang",
  show_update: "Firmware-Update",
  show_speed: "Tempo",
  show_model: "Modell",
  show_type: "Gerätetyp",
  show_last_seen: "Zuletzt online",
  show_vendor: "Hersteller (aus der MAC-Adresse)",
  show_band: "Funkband (2,4 / 5 GHz)",
  show_connected_via: "Verbunden über (Mesh)",
  show_label: "Etikett",
  show_note: "Notiz",
  group_by: "Gruppierung",
  show_group_select: "Gruppierungs-Auswahl anzeigen",
  show_csv_export: "CSV-Export-Knopf anzeigen",
  remember_view: "Filter, Sortierung und Gruppierung merken",
  mac_click_copies: "Klick auf die MAC-Adresse kopiert sie",
  show_summary: "Zusammenfassung anzeigen",
  show_search: "Suchfeld anzeigen",
  show_filter: "Filterleiste anzeigen",
  show_controls: "Steuerungsleiste anzeigen",
  show_version: "Version und Update-Hinweis anzeigen",
  show_parental: "Zugangsprofil (Kindersicherung) im Popup anzeigen",
  show_tabs: "Kategorien als Tabs anzeigen",
  filter_alle: "Button „Alle“",
  filter_aktiv: "Button „Aktiv“",
  filter_inaktiv: "Button „Inaktiv“",
  filter_gast: "Button „Gast“",
  filter_gesperrt: "Button „Gesperrt“",
  filter_update: "Button „Update“",
  filter_fest: "Button „Feste IP“",
  filter_neu: "Button „Neu (7 Tage)“",
  filter_lange_offline: "Button „Lange offline“",
  hide_inactive: "Nicht verbundene Geräte ausblenden",
  compact: "Kompakte Zeilen",
  show_details_popup: "Klick öffnet ein Detail-Popup",
  open_device_on_click: "Klick öffnet das Home-Assistant-Gerät",
  show_scroll_arrows: "Blätter-Pfeile bei breiter Tabelle",
  sticky_name: "Gerätename beim Blättern festhalten",
  ip_opens_web: "Klick auf die IP öffnet die Weboberfläche",
  ip_web_fallback: "Notfalls http://IP verwenden",
  max_rows: "Höchstzahl Zeilen (0 = alle)",
  max_visible_rows: "Sichtbare Zeilen, dann scrollen (0 = alle)",
  sort_by: "Sortieren nach",
  sort_dir: "Richtung",
  default_filter: "Standardfilter beim Laden",
};

const EDITOR_HELPERS = {
  show_tabs: "Zeigt oben Reiter für die Kategorien Netzwerk und Steuerung. Jeder Reiter zeigt ausschließlich seine eigenen Elemente: Netzwerk die Filter, die Suche und die Geräteliste, Steuerung die Down/Up-Anzeige, die WLAN-Schalter und Neuverbinden/Neustart. Der Steuerungs-Reiter erscheint nur, wenn die Steuerungsleiste aktiviert ist. Ohne Reiter erscheinen beide Bereiche wie bisher untereinander.",
  show_controls: "Zeigt in der Karte eine Leiste mit Live-Down/Up sowie – wenn die FRITZ!Box-Steuerung in den Integrationseinstellungen aktiviert ist – WLAN-Schaltern, MAC-Filter/Pairing und den Buttons Neuverbinden/Neustart. Gibt es Repeater, erscheint zusätzlich die Mesh-Gruppe (FRITZ!Box + Repeater) mit „Alle neu starten“.",
  show_version: "Zeigt auf der Steuerungsseite die Version der Integration. Gibt es eine neuere Version, wird sie farblich hervorgehoben.",
  show_parental: "Zeigt im Geräte-Popup die Auswahl des Zugangsprofils (Kindersicherung). Erscheint nur, wenn die Funktion in den Integrationsoptionen eingeschaltet ist.",
  default_filter: "Welcher Filter aktiv ist, wenn die Karte geladen oder neu geöffnet wird (z. B. „Aktiv“). Nach einem Refresh wird nicht mehr auf „Alle“ zurückgesetzt.",
  language: "Sprache der Beschriftungen in der Karte. „Automatisch“ folgt der in Home Assistant eingestellten Sprache (Deutsch, Englisch, Niederländisch).",
  show_title: "Blendet die Kopfzeile der Karte aus, z. B. für ein Popup oder eine kompakte Ansicht.",
  ip_filter: "Zeigt nur Geräte, deren IP-Adresse passt – so lässt sich das Netz auf mehrere Karten verteilen (z. B. eine Karte „192.168.2.*“ für Drucker, eine „192.168.3.*“ für Lichter). „*“ steht für beliebig viele, „?“ für genau ein Zeichen. Mehrere Muster mit Komma oder Leerzeichen trennen; ein „!“ davor schließt aus (z. B. „192.168.1.* !192.168.1.1“). Leer = alle Geräte. Geräte ohne IP-Adresse werden bei gesetztem Filter nicht angezeigt. Die Zusammenfassung zählt dann nur diese Geräte.",
  show_ip_type: "Braucht die eingeschaltete IP-Typ-Erfassung in den Einstellungen der Integration.",
  show_ha_name: "Zeigt den Gerätenamen aus Home Assistant, sofern das Gerät dort eine MAC-Adresse hinterlegt hat. Ein Klick auf den Namen führt direkt zum Gerät.",
  show_band: "Zeigt, in welchem WLAN-Band ein Gerät gerade verbunden ist (2,4, 5 oder 6 GHz). Die Integration liest dazu die WLAN-Geräteliste der FRITZ!Box (Einstellung „WLAN-Band je Gerät erfassen“ der Integration). Geräte ohne WLAN-Verbindung zur Box – LAN, offline oder an einem Repeater, den die Box nicht selbst versorgt – zeigen „—“. Nur Anzeige: Ein Gerät einem Band zuzuweisen kann die FRITZ!Box nicht.",
  show_label: "Zeigt das eigene Etikett (z. B. „Kinderzimmer“). Etiketten und Notizen werden im Detail-Popup über den Stift bearbeitet und nur in Home Assistant gespeichert – die FRITZ!Box wird nicht verändert.",
  remember_view: "Merkt Filter, Sortierung, Gruppierung und eingeklappte Gruppen pro Browser (localStorage). Ändert man die Startwerte in dieser Konfiguration, gilt wieder die neue Vorgabe.",
  show_connected_via: "Zeigt den Mesh-Nachbarn (FRITZ!Box oder Repeater), über den ein Gerät gerade verbunden ist, mit der aktuellen Verbindungsrate als Tooltip. Braucht mindestens einen FRITZ!-Mesh-Repeater im Heimnetz; bei nur einer FRITZ!Box bleibt die Spalte leer. Die genaue Mesh-Datenstruktur der FRITZ!Box ist nicht an jeder Hardware/FRITZ!OS-Version geprüft – fehlt die Angabe bei einem Gerät, zeigt die Box dafür vermutlich keine eindeutige Verbindung.",
  filter_fest: "Zeigt nur Geräte mit fester IP-Adresse – am Gerät eingestellt oder von der FRITZ!Box reserviert – aktive und inaktive. Braucht die IP-Typ-Erfassung in den Einstellungen der Integration. Eine Reservierung innerhalb des DHCP-Bereichs meldet die FRITZ!Box nicht; solche Geräte gelten als „dynamisch“.",
  filter_neu: "Zeigt nur Geräte, die in den letzten 7 Tagen zum ersten Mal im Heimnetz aufgetaucht sind. Bereits vor der Installation dieser Funktion bekannte Geräte gelten nicht als „neu“.",
  filter_lange_offline: "Zeigt nur inaktive Geräte, die seit mindestens 30 Tagen nicht mehr gesehen wurden (oder noch nie, seit die Integration das erfasst). Daneben erscheint ein Knopf, um Namen und MAC-Adressen dieser Geräte zum Aufräumen zu kopieren.",
  show_vendor: "Zeigt den Hersteller, der zum Anfang der MAC-Adresse gehört (aus einer mitgelieferten Liste des IEEE, ohne Internetzugriff). Hilft, ein Gerät mit unklarem Namen zu erkennen. Smartphones mit „Privater WLAN-Adresse“ nutzen zufällige Adressen – dort steht „Zufällige MAC“.",
  mac_click_copies: "Ein Klick auf die MAC-Adresse in der Tabelle kopiert sie in die Zwischenablage, statt das Detail-Popup zu öffnen. Ohne HTTPS nutzt die Karte eine Ausweichmethode; klappt auch die nicht, erscheint ein Hinweis. Im Popup bleibt der Kopier-Knopf.",
  show_last_seen: "Wann ein Gerät zuletzt online war. Die FRITZ!Box liefert das nicht – die Integration schreibt es ab Installation selbst mit und speichert es dauerhaft.",
  show_details_popup: "Zeigt beim Antippen alle Felder eines Geräts, auch die auf schmalen Karten ausgeblendeten wie die MAC-Adresse.",
  open_device_on_click: "Wirkt nur, wenn das Detail-Popup ausgeschaltet ist.",
  show_scroll_arrows: "Passen nicht alle Spalten nebeneinander (z. B. auf dem Smartphone), wird die Tabelle waagerecht scrollbar. Diese Pfeile blättern zusätzlich per Klick; wischen geht auch direkt.",
  sticky_name: "Beim waagerechten Blättern bleiben Statuspunkt und Gerätename links stehen.",
  ip_opens_web: "Öffnet die von der FRITZ!Box gemeldete Geräteseite in einem neuen Browser-Tab.",
  ip_web_fallback: "Meldet die FRITZ!Box keine Adresse, wird http://<IP> versucht. Kann bei Geräten ohne Weboberfläche ins Leere laufen.",
  max_rows: "Begrenzt die Tabelle, zum Beispiel für eine Übersichtskarte.",
  max_visible_rows: "Ab dieser Zeilenzahl wird der Datenbereich scrollbar; Titel, Auswahl und Tabellenüberschrift bleiben stehen. 0 zeigt alle Zeilen.",
};

const EDITOR_TX = {
  de: {
    group_columns: "Spalten", group_display: "Darstellung",
    group_filter: "Filter-Buttons", group_sort: "Sortierung",
    colors_title: "Farben", reset: "Alle Farben zurücksetzen",
    note_theme: "aktuell: Standard des Themes ({v})", note_current: "aktuell: {v}",
    invalid: "Wert nicht gültig", asc: "Aufsteigend", desc: "Absteigend",
    lang_auto: "Automatisch (Home Assistant)",
  },
  en: {
    entity: "Sensor with the device list", title: "Title", show_title: "Show title",
    language: "Card language",
    ip_filter: "IP filter (wildcards allowed)",
    help_ip_filter: "Shows only devices whose IP address matches, so the network can be split across several cards (e.g. one card \"192.168.2.*\" for printers, one \"192.168.3.*\" for lights). \"*\" stands for any number of characters, \"?\" for exactly one. Separate several patterns with a comma or space; a leading \"!\" excludes (e.g. \"192.168.1.* !192.168.1.1\"). Empty = all devices. With a filter set, devices without an IP address are not shown. The summary then counts only these devices.",
    show_status: "Status", show_name: "Device", show_ip: "IP address",
    show_mac: "MAC address", show_connection: "Connection",
    show_ha_name: "Home Assistant device name (linked)",
    show_ip_type: "IP type (DHCP or static)", show_wan: "Internet access",
    show_update: "Firmware update", show_speed: "Speed", show_model: "Model",
    show_type: "Device type", show_last_seen: "Last seen",
    show_vendor: "Manufacturer (from the MAC address)",
    show_band: "Wi-Fi band (2.4 / 5 GHz)",
    show_connected_via: "Connected via (mesh)",
    show_label: "Label",
    show_note: "Note",
    group_by: "Grouping",
    show_group_select: "Show grouping selector",
    show_csv_export: "Show CSV export button",
    remember_view: "Remember filter, sorting and grouping",
    mac_click_copies: "Clicking the MAC address copies it",
    help_show_band: "Shows which Wi-Fi band a device is currently connected on (2.4, 5 or 6 GHz). The integration reads the FRITZ!Box Wi-Fi device list for this (integration setting \"Track Wi-Fi band per device\"). Devices without a Wi-Fi connection to the box - wired, offline, or behind a repeater the box does not serve itself - show \"\u2014\". Display only: the FRITZ!Box cannot assign a device to a band.",
    help_show_connected_via: "Shows the mesh neighbor (FRITZ!Box or repeater) a device is currently connected through, with the current link rate as a tooltip. Needs at least one FRITZ! mesh repeater on the network; with a single FRITZ!Box the column stays empty. The FRITZ!Box's exact mesh data structure has not been verified on every hardware/FRITZ!OS version \u2013 if a device is missing this value, the box likely does not report one clear connection for it.",
    help_filter_fest: "Shows only devices with a fixed IP address - set on the device or reserved by the FRITZ!Box - active and inactive. Needs IP type tracking in the integration settings. The FRITZ!Box does not report a reservation inside the DHCP range; such devices count as \"dynamic\".",
    help_filter_neu: "Shows only devices that first appeared on the network within the last 7 days. Devices already known before this feature was installed do not count as \"new\".",
    help_filter_lange_offline: "Shows only inactive devices not seen for at least 30 days (or never, since the integration started tracking this). Also shows a button to copy these devices' names and MAC addresses for cleanup.",
    help_show_vendor: "Shows the manufacturer that belongs to the start of the MAC address (from a bundled IEEE list, no internet access needed). Helps to recognize a device with an unclear name. Smartphones with a \u201cPrivate Wi-Fi address\u201d use random addresses \u2013 those show \u201cRandom MAC\u201d.",
    help_mac_click_copies: "A click on the MAC address in the table copies it to the clipboard instead of opening the detail popup. Without HTTPS the card uses a fallback method; if that fails too, a notice appears. The popup keeps its copy button.",
    show_summary: "Show summary", show_search: "Show search field",
    show_filter: "Show filter bar",
    show_controls: "Show controls bar",
    show_version: "Show version and update notice",
    show_parental: "Show access profile (parental control) in the popup",
    show_tabs: "Show categories as tabs",
    help_show_tabs: "Shows tabs for the Network and Controls categories at the top. Each tab shows only its own elements: Network the filters, search and device list, Controls the download/upload display, Wi-Fi switches and reconnect/reboot. The Controls tab only appears when the controls bar is enabled. Without tabs, both areas appear below each other as before.",
    help_show_controls: "Shows a bar with live download/upload and \u2013 if FRITZ!Box controls are enabled in the integration settings \u2013 Wi-Fi switches, MAC filter/pairing and reconnect/reboot buttons. If there are repeaters, a mesh group (FRITZ!Box + repeaters) with \u201cRestart all\u201d is shown as well.",
    help_show_version: "Shows the integration version on the controls page. If a newer version exists it is highlighted in colour.",
    help_show_parental: "Shows the access profile selection (parental control) in the device popup. Only appears if the feature is enabled in the integration options.",
    filter_alle: '"All" button', filter_aktiv: '"Active" button',
    filter_inaktiv: '"Inactive" button', filter_gast: '"Guest" button',
    filter_gesperrt: '"Blocked" button', filter_update: '"Update" button', filter_fest: '"Fixed IP" button', filter_neu: '"New (7 days)" button', filter_lange_offline: '"Long offline" button',
    hide_inactive: "Hide disconnected devices", compact: "Compact rows",
    show_details_popup: "Click opens a detail popup",
    open_device_on_click: "Click opens the Home Assistant device",
    show_scroll_arrows: "Scroll arrows on wide tables",
    sticky_name: "Keep device name while scrolling",
    ip_opens_web: "Click on the IP opens the web interface",
    ip_web_fallback: "Fall back to http://IP",
    max_rows: "Maximum rows (0 = all)",
    max_visible_rows: "Visible rows, then scroll (0 = all)",
    sort_by: "Sort by", sort_dir: "Direction",
    default_filter: "Default filter on load",
    help_default_filter: "Which filter is active when the card loads or is reopened (e.g. \"Active\"). After a refresh it no longer resets to \"All\".",
    help_language: 'Language of the card labels. "Automatic" follows the language configured in Home Assistant (German, English, Dutch).',
    help_show_title: "Hides the card header, e.g. for a popup or a compact view.",
    help_show_ip_type: "Requires IP type tracking enabled in the integration settings.",
    help_show_ha_name: "Shows the device name from Home Assistant if the device has a MAC address there. Clicking the name goes straight to the device.",
    help_show_last_seen: "When a device was last online. The FRITZ!Box does not provide this – the integration records it from installation onward and stores it permanently.",
    help_show_details_popup: "Shows all fields of a device on tap, including those hidden on narrow cards such as the MAC address.",
    help_open_device_on_click: "Only applies when the detail popup is disabled.",
    help_show_scroll_arrows: "If not all columns fit side by side (e.g. on a phone), the table scrolls horizontally. These arrows page on click; swiping works too.",
    help_sticky_name: "While scrolling horizontally, the status dot and device name stay on the left.",
    help_ip_opens_web: "Opens the device page reported by the FRITZ!Box in a new browser tab.",
    help_ip_web_fallback: "If the FRITZ!Box reports no address, http://<IP> is tried. May lead nowhere for devices without a web interface.",
    help_max_rows: "Limits the table, for example for an overview card.",
    help_max_visible_rows: "From this row count the data area becomes scrollable; title, selection and table header stay fixed. 0 shows all rows.",
    group_columns: "Columns", group_display: "Appearance",
    group_filter: "Filter buttons", group_sort: "Sorting",
    colors_title: "Colors", reset: "Reset all colors",
    note_theme: "current: theme default ({v})", note_current: "current: {v}",
    invalid: "invalid value", asc: "Ascending", desc: "Descending",
    lang_auto: "Automatic (Home Assistant)",
    color_header_bg: "Header background", color_header_text: "Header text",
    color_row_text: "Row text", color_row_alt_bg: "Every other row",
    color_border: "Divider lines", color_active: "Active",
    color_inactive: "Inactive", color_guest: "Guest network",
    color_blocked: "Blocked", color_update: "Update available",
    color_static: "Static IP", color_accent: "Accent (sorting, filter)",
    color_cat_alle: "Icon category \"All\"", color_cat_aktiv: "Icon category \"Active\"", color_cat_inaktiv: "Icon category \"Inactive\"", color_cat_gast: "Icon category \"Guest\"", color_cat_gesperrt: "Icon category \"Blocked\"", color_cat_update: "Icon category \"Update\"", color_cat_fest: "Icon category \"Fixed IP\"",
  },
  nl: {
    entity: "Sensor met de apparaatlijst", title: "Titel", show_title: "Titel tonen",
    language: "Taal van de kaart",
    ip_filter: "IP-filter (jokertekens toegestaan)",
    help_ip_filter: "Toont alleen apparaten waarvan het IP-adres overeenkomt, zodat het netwerk over meerdere kaarten kan worden verdeeld (bijv. een kaart \"192.168.2.*\" voor printers, een kaart \"192.168.3.*\" voor lampen). \"*\" staat voor een willekeurig aantal tekens, \"?\" voor precies één teken. Scheid meerdere patronen met een komma of spatie; een \"!\" ervoor sluit uit (bijv. \"192.168.1.* !192.168.1.1\"). Leeg = alle apparaten. Bij een ingesteld filter worden apparaten zonder IP-adres niet getoond. De samenvatting telt dan alleen deze apparaten.",
    show_status: "Status", show_name: "Apparaat", show_ip: "IP-adres",
    show_mac: "MAC-adres", show_connection: "Verbinding",
    show_ha_name: "Home Assistant-apparaatnaam (gelinkt)",
    show_ip_type: "IP-type (DHCP of statisch)", show_wan: "Internettoegang",
    show_update: "Firmware-update", show_speed: "Snelheid", show_model: "Model",
    show_type: "Apparaattype", show_last_seen: "Laatst online",
    show_vendor: "Fabrikant (uit het MAC-adres)",
    show_band: "Wifi-band (2,4 / 5 GHz)",
    show_connected_via: "Verbonden via (mesh)",
    show_label: "Label",
    show_note: "Notitie",
    group_by: "Groepering",
    show_group_select: "Groeperingskeuze tonen",
    show_csv_export: "CSV-exportknop tonen",
    remember_view: "Filter, sortering en groepering onthouden",
    mac_click_copies: "Klik op het MAC-adres kopieert het",
    help_show_band: "Toont op welke wifi-band een apparaat nu verbonden is (2,4, 5 of 6 GHz). De integratie leest hiervoor de wifi-apparatenlijst van de FRITZ!Box (instelling \"Wifi-band per apparaat bijhouden\"). Apparaten zonder wifi-verbinding met de box - bekabeld, offline of achter een repeater die de box niet zelf bedient - tonen \"\u2014\". Alleen weergave: de FRITZ!Box kan een apparaat niet aan een band toewijzen.",
    help_show_connected_via: "Toont de meshbuur (FRITZ!Box of repeater) waarmee een apparaat nu verbonden is, met de huidige verbindingssnelheid als tooltip. Vereist minstens \u00e9\u00e9n FRITZ!-meshrepeater in het netwerk; met slechts \u00e9\u00e9n FRITZ!Box blijft de kolom leeg. De exacte meshgegevensstructuur van de FRITZ!Box is niet op elke hardware/FRITZ!OS-versie getest \u2013 ontbreekt deze waarde bij een apparaat, dan meldt de box daarvoor waarschijnlijk geen eenduidige verbinding.",
    help_filter_fest: "Toont alleen apparaten met een vast IP-adres - op het apparaat ingesteld of door de FRITZ!Box gereserveerd - actief en inactief. Vereist het bijhouden van het IP-type in de integratie-instellingen. Een reservering binnen het DHCP-bereik meldt de FRITZ!Box niet; zulke apparaten gelden als \"dynamisch\".",
    help_filter_neu: "Toont alleen apparaten die in de afgelopen 7 dagen voor het eerst in het netwerk zijn verschenen. Apparaten die al bekend waren voordat deze functie werd geïnstalleerd, gelden niet als \"nieuw\".",
    help_filter_lange_offline: "Toont alleen inactieve apparaten die minstens 30 dagen niet zijn gezien (of nooit, sinds de integratie dit bijhoudt). Toont ook een knop om namen en MAC-adressen van deze apparaten te kopiëren voor opschoning.",
    help_show_vendor: "Toont de fabrikant die bij het begin van het MAC-adres hoort (uit een meegeleverde IEEE-lijst, zonder internettoegang). Helpt een apparaat met een onduidelijke naam te herkennen. Smartphones met een \u201cPrivé wifi-adres\u201d gebruiken willekeurige adressen \u2013 daar staat \u201cWillekeurig MAC\u201d.",
    help_mac_click_copies: "Een klik op het MAC-adres in de tabel kopieert het naar het klembord in plaats van het detailvenster te openen. Zonder HTTPS gebruikt de kaart een terugvalmethode; lukt die ook niet, dan verschijnt een melding. Het detailvenster houdt zijn kopieerknop.",
    show_summary: "Samenvatting tonen", show_search: "Zoekveld tonen",
    show_filter: "Filterbalk tonen",
    show_controls: "Bedieningsbalk tonen",
    show_version: "Versie en updatemelding tonen",
    show_parental: "Toegangsprofiel (ouderlijk toezicht) in de popup tonen",
    show_tabs: "Categorieën als tabs tonen",
    help_show_tabs: "Toont bovenaan tabs voor de categorieën Netwerk en Bediening. Elke tab toont uitsluitend de eigen elementen: Netwerk de filters, het zoekveld en de apparatenlijst, Bediening de download/upload-weergave, de wifi-schakelaars en opnieuw verbinden/herstarten. De tab Bediening verschijnt alleen als de bedieningsbalk is ingeschakeld. Zonder tabs verschijnen beide gebieden onder elkaar zoals voorheen.",
    help_show_controls: "Toont een balk met live download/upload en \u2013 als de FRITZ!Box-bediening in de integratie-instellingen is ingeschakeld \u2013 wifi-schakelaars, MAC-filter/koppelen en knoppen voor opnieuw verbinden/herstarten. Als er repeaters zijn, verschijnt ook de meshgroep (FRITZ!Box + repeaters) met \u201cAlles herstarten\u201d.",
    help_show_version: "Toont op de bedieningspagina de versie van de integratie. Is er een nieuwere versie, dan wordt die gekleurd gemarkeerd.",
    help_show_parental: "Toont in de apparaat-popup de keuze van het toegangsprofiel (ouderlijk toezicht). Verschijnt alleen als de functie in de integratie-opties is ingeschakeld.",
    filter_alle: 'Knop "Alle"', filter_aktiv: 'Knop "Actief"',
    filter_inaktiv: 'Knop "Inactief"', filter_gast: 'Knop "Gast"',
    filter_gesperrt: 'Knop "Geblokkeerd"', filter_update: 'Knop "Update"', filter_fest: 'Knop "Vast IP"', filter_neu: 'Knop "Nieuw (7 dagen)"', filter_lange_offline: 'Knop "Lang offline"',
    hide_inactive: "Niet-verbonden apparaten verbergen", compact: "Compacte rijen",
    show_details_popup: "Klik opent een detailvenster",
    open_device_on_click: "Klik opent het Home Assistant-apparaat",
    show_scroll_arrows: "Bladerpijlen bij brede tabel",
    sticky_name: "Apparaatnaam vasthouden bij bladeren",
    ip_opens_web: "Klik op het IP opent de webinterface",
    ip_web_fallback: "Zo nodig http://IP gebruiken",
    max_rows: "Maximaal aantal rijen (0 = alle)",
    max_visible_rows: "Zichtbare rijen, dan scrollen (0 = alle)",
    sort_by: "Sorteren op", sort_dir: "Richting",
    default_filter: "Standaardfilter bij laden",
    help_default_filter: "Welk filter actief is als de kaart wordt geladen of opnieuw geopend (bijv. \"Actief\"). Na een refresh wordt niet meer teruggezet naar \"Alle\".",
    help_language: 'Taal van de kaartlabels. "Automatisch" volgt de in Home Assistant ingestelde taal (Duits, Engels, Nederlands).',
    help_show_title: "Verbergt de kop van de kaart, bijv. voor een pop-up of een compacte weergave.",
    help_show_ip_type: "Vereist dat het bijhouden van het IP-type is ingeschakeld in de integratie-instellingen.",
    help_show_ha_name: "Toont de apparaatnaam uit Home Assistant als het apparaat daar een MAC-adres heeft. Klikken op de naam gaat direct naar het apparaat.",
    help_show_last_seen: "Wanneer een apparaat laatst online was. De FRITZ!Box levert dit niet – de integratie houdt het vanaf de installatie zelf bij en slaat het permanent op.",
    help_show_details_popup: "Toont bij tikken alle velden van een apparaat, ook die op smalle kaarten verborgen zijn zoals het MAC-adres.",
    help_open_device_on_click: "Werkt alleen als het detailvenster is uitgeschakeld.",
    help_show_scroll_arrows: "Passen niet alle kolommen naast elkaar (bijv. op een telefoon), dan schuift de tabel horizontaal. Deze pijlen bladeren ook per klik; vegen kan ook.",
    help_sticky_name: "Bij horizontaal bladeren blijven de statusstip en de apparaatnaam links staan.",
    help_ip_opens_web: "Opent de door de FRITZ!Box gemelde apparaatpagina in een nieuw browsertabblad.",
    help_ip_web_fallback: "Meldt de FRITZ!Box geen adres, dan wordt http://<IP> geprobeerd. Kan doodlopen bij apparaten zonder webinterface.",
    help_max_rows: "Beperkt de tabel, bijvoorbeeld voor een overzichtskaart.",
    help_max_visible_rows: "Vanaf dit aantal rijen wordt het gegevensgebied scrollbaar; titel, selectie en tabelkop blijven staan. 0 toont alle rijen.",
    group_columns: "Kolommen", group_display: "Weergave",
    group_filter: "Filterknoppen", group_sort: "Sorteren",
    colors_title: "Kleuren", reset: "Alle kleuren resetten",
    note_theme: "huidig: standaard van het thema ({v})", note_current: "huidig: {v}",
    invalid: "ongeldige waarde", asc: "Oplopend", desc: "Aflopend",
    lang_auto: "Automatisch (Home Assistant)",
    color_header_bg: "Kop-achtergrond", color_header_text: "Kop-tekst",
    color_row_text: "Rij-tekst", color_row_alt_bg: "Elke tweede rij",
    color_border: "Scheidingslijnen", color_active: "Actief",
    color_inactive: "Inactief", color_guest: "Gastnetwerk",
    color_blocked: "Geblokkeerd", color_update: "Update beschikbaar",
    color_static: "Statisch IP", color_accent: "Accent (sorteren, filter)",
    color_cat_alle: "Pictogram categorie \"Alle\"", color_cat_aktiv: "Pictogram categorie \"Actief\"", color_cat_inaktiv: "Pictogram categorie \"Inactief\"", color_cat_gast: "Pictogram categorie \"Gast\"", color_cat_gesperrt: "Pictogram categorie \"Geblokkeerd\"", color_cat_update: "Pictogram categorie \"Update\"", color_cat_fest: "Pictogram categorie \"Vast IP\"",
  },
};

class FritzboxNetzwerkCardEditor extends HTMLElement {
  constructor() {
    super();
    this._config = withDefaults({});
    this._hass = null;
    this._rendered = false;
    this._focusedColorKey = null;
    // Siehe _preserveClearedTitle(): true, sobald der Nutzer den Titel
    // absichtlich auf "" geleert hat (nicht nur, wenn er aktuell leer IST -
    // das war der Fehler in der 1.6.2-Fassung dieses Fixes).
    this._titleCleared = false;
  }

  setConfig(config) {
    this._config = withDefaults(this._preserveClearedTitle(config));
    this._render();
    this._applyLanguage();
  }

  /**
   * Schuetzt einen vom Nutzer bewusst geleerten Titel vor withDefaults().
   *
   * Home Assistant entfernt ein leeres, optionales Textfeld beim
   * Zwischenspeichern aus der Kartenkonfiguration (um keine leeren
   * Strings in der YAML zu hinterlassen) und ruft danach setConfig()
   * erneut mit dieser bereinigten Konfiguration auf. Fehlt "title"
   * dadurch komplett, wuerde withDefaults() den Standardwert
   * "Netzwerkgeräte" wieder eintragen.
   *
   * Der 1.6.2-Fix hat das ueber einen Truthy-Check auf this._config.title
   * erkannt - das schlug aber ausgerechnet beim Loeschen des LETZTEN
   * Buchstabens fehl: in dem Moment ist this._config.title bereits selbst
   * "" (vom internen ha-form-Listener gesetzt, siehe _render()), ein
   * Truthy-Check haelt "" faelschlich fuer "nie gesetzt" und das Feld
   * sprang wieder auf "Netzwerkgeräte" zurueck - exakt der Fall, den ein
   * Nutzer nach 1.6.2 gemeldet hat. Jetzt wird stattdessen in
   * this._titleCleared gemerkt, OB der Nutzer zuletzt explizit "" gesetzt
   * hat (das Flag bleibt auch dann true, wenn der String selbst schon
   * leer ist). Nur bei einer bereits gerenderten Karte greift der Schutz,
   * damit eine wirklich neue Karte (noch kein Titel je gesetzt) weiterhin
   * "Netzwerkgeräte" als Startwert zeigt.
   */
  _preserveClearedTitle(config) {
    const incoming = { ...(config || {}) };
    if ("title" in incoming) {
      this._titleCleared = incoming.title === "";
    } else if (this._rendered && this._titleCleared) {
      incoming.title = "";
    }
    return incoming;
  }

  set hass(hass) {
    this._hass = hass;
    if (this._form) this._form.hass = hass;
    this._applyLanguage();
  }

  /* -- Sprache des Editors ------------------------------------------ */

  _edLang() {
    return resolveLang(this._config, this._hass);
  }

  /** Beschriftung eines Konfigurationsfeldes in der Editor-Sprache. */
  _edLabel(name) {
    const lang = this._edLang();
    if (lang !== "de" && EDITOR_TX[lang] && EDITOR_TX[lang][name]) {
      return EDITOR_TX[lang][name];
    }
    return EDITOR_LABELS[name] || name;
  }

  /** Hilfetext eines Feldes in der Editor-Sprache (oder leer). */
  _edHelper(name) {
    const lang = this._edLang();
    if (lang !== "de" && EDITOR_TX[lang] && EDITOR_TX[lang][`help_${name}`]) {
      return EDITOR_TX[lang][`help_${name}`];
    }
    return EDITOR_HELPERS[name] || "";
  }

  /** Sonstige Editor-Texte (Gruppen, Farben, Notizen) in der Editor-Sprache. */
  _edUI(key, params) {
    const lang = this._edLang();
    const table = EDITOR_TX[lang] || EDITOR_TX.de;
    let text = table[key];
    if (text === undefined) text = EDITOR_TX.de[key];
    if (text === undefined) return key;
    if (params) {
      for (const name of Object.keys(params)) {
        text = text.replace(new RegExp(`\\{${name}\\}`, "g"), String(params[name]));
      }
    }
    return text;
  }

  /** Farb-Beschriftung in der Editor-Sprache (DE aus COLOR_EDITOR_FIELDS). */
  _edColorLabel(field) {
    const lang = this._edLang();
    if (lang !== "de" && EDITOR_TX[lang] && EDITOR_TX[lang][field.key]) {
      return EDITOR_TX[lang][field.key];
    }
    return field.label;
  }

  /** Baut das ha-form-Schema mit übersetzten Gruppentiteln und Auswahllisten. */
  _localizedSchema() {
    const lang = this._edLang();
    const groups = {
      spalten: "group_columns",
      darstellung: "group_display",
      filter_buttons: "group_filter",
      sortierung: "group_sort",
    };
    const localizeField = (field) => {
      if (field.name === "sort_by") {
        return {
          ...field,
          selector: {
            select: {
              mode: "dropdown",
              options: COLUMNS.map((column) => ({
                value: column.key,
                label: translate(lang, `col.${column.key}`),
              })),
            },
          },
        };
      }
      if (field.name === "sort_dir") {
        return {
          ...field,
          selector: {
            select: {
              mode: "dropdown",
              options: [
                { value: "asc", label: this._edUI("asc") },
                { value: "desc", label: this._edUI("desc") },
              ],
            },
          },
        };
      }
      if (field.name === "default_filter") {
        return {
          ...field,
          selector: {
            select: {
              mode: "dropdown",
              options: FILTERS.map((filter) => ({
                value: filter.key,
                label: translate(lang, `flt.${filter.key}`),
              })),
            },
          },
        };
      }
      if (field.name === "group_by") {
        return {
          ...field,
          selector: {
            select: {
              mode: "dropdown",
              options: [{ value: "", label: translate(lang, "group.none") }].concat(
                GROUP_MODES.map((mode) => ({ value: mode, label: translate(lang, `group.${mode}`) }))
              ),
            },
          },
        };
      }
      if (field.name === "language") {
        return {
          ...field,
          selector: {
            select: {
              mode: "dropdown",
              options: [
                { value: "", label: this._edUI("lang_auto") },
                { value: "de", label: "Deutsch" },
                { value: "en", label: "English" },
                { value: "nl", label: "Nederlands" },
              ],
            },
          },
        };
      }
      return field;
    };
    return EDITOR_SCHEMA.map((entry) => {
      if (entry.type === "expandable") {
        return {
          ...entry,
          title: this._edUI(groups[entry.name] || entry.name),
          schema: entry.schema.map(localizeField),
        };
      }
      return localizeField(entry);
    });
  }

  /** Wendet die aktuelle Sprache auf Formular und Farbbereich an. */
  _applyLanguage() {
    if (!this._rendered || !this._form) return;
    this._form.schema = this._localizedSchema();
    this._form.computeLabel = (schema) => this._edLabel(schema.name);
    this._form.computeHelper = (schema) => this._edHelper(schema.name);
    this._form.data = this._config;
    const title = this.querySelector(".fbn-color-title");
    if (title) title.textContent = this._edUI("colors_title");
    const reset = this.querySelector(".fbn-reset");
    if (reset) {
      reset.innerHTML = `<ha-icon icon="mdi:restore"></ha-icon>${escapeHtml(
        this._edUI("reset")
      )}`;
    }
    this._renderColors();
  }

  _fire(config) {
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config },
        bubbles: true,
        composed: true,
      })
    );
  }

  _render() {
    if (!this._rendered) {
      this.innerHTML = `
        <style>${this._styles()}</style>
        <div class="fbn-editor">
          <div class="fbn-form"></div>
          <details class="fbn-color-editor">
            <summary>
              <ha-icon icon="mdi:palette-outline"></ha-icon>
              <span class="fbn-color-title">Farben</span>
              <ha-icon class="fbn-color-chevron" icon="mdi:chevron-down"></ha-icon>
            </summary>
            <div class="fbn-color-body">
              <button type="button" class="fbn-reset"><ha-icon icon="mdi:restore"></ha-icon>Alle Farben zurücksetzen</button>
              <div class="fbn-color-rows"></div>
            </div>
          </details>
        </div>`;

      this._form = document.createElement("ha-form");
      this._form.schema = EDITOR_SCHEMA;
      this._form.computeLabel = (schema) =>
        EDITOR_LABELS[schema.name] || schema.title || schema.name;
      this._form.computeHelper = (schema) => EDITOR_HELPERS[schema.name] || "";
      this._form.addEventListener("value-changed", (event) => {
        event.stopPropagation();
        // _titleCleared hier schon pflegen, nicht erst in setConfig():
        // ha-form liefert bei einem geleerten Textfeld "title": "" (anders
        // als der spaetere Umweg ueber Home Assistants eigenen
        // Konfigurations-Rahmen, der das Feld ganz entfernt, siehe
        // _preserveClearedTitle()).
        if ("title" in event.detail.value) {
          this._titleCleared = event.detail.value.title === "";
        }
        this._config = withDefaults({ ...this._config, ...event.detail.value });
        this._fire(this._config);
      });
      this.querySelector(".fbn-form").appendChild(this._form);

      this.querySelector(".fbn-reset").addEventListener("click", () => {
        // Der Fokusschutz wird hier bewusst uebergangen: ein Klick auf
        // "Zuruecksetzen" ist eine ausdrueckliche Nutzerentscheidung.
        this._focusedColorKey = null;
        const config = { ...this._config };
        for (const field of COLOR_EDITOR_FIELDS) config[field.key] = "";
        this._config = config;
        this._fire(config);
        this._renderColors();
      });

      this._rendered = true;
    }

    if (this._hass) this._form.hass = this._hass;
    this._form.data = this._config;
    this._renderColors();
  }

  _renderColors() {
    const container = this.querySelector(".fbn-color-rows");
    if (!container) return;

    container.innerHTML = COLOR_EDITOR_FIELDS.map((field) => {
      const raw = this._config[field.key] || "";
      const safe = sanitizeColor(raw);
      const effective = safe || COLOR_FALLBACKS[field.key];
      const hex = normalizeHex(safe) || "#888888";
      const label = this._edColorLabel(field);
      const note = safe
        ? this._edUI("note_current", { v: safe })
        : this._edUI("note_theme", { v: COLOR_FALLBACKS[field.key] });
      const invalid =
        raw && !safe
          ? `<span class="fbn-invalid">${escapeHtml(this._edUI("invalid"))}</span>`
          : "";
      return `
        <div class="fbn-color-row" data-key="${field.key}">
          <div class="fbn-color-meta">
            <span class="fbn-color-label">${escapeHtml(label)}</span>
            <span class="fbn-color-note">${escapeHtml(note)}</span>
            ${invalid}
          </div>
          <div class="fbn-color-controls">
            <span class="fbn-color-preview" style="background:${effective}"></span>
            <input class="fbn-color-text" type="text" value="${escapeHtml(raw)}"
                   placeholder="z. B. #4caf50" aria-label="${escapeHtml(label)}">
            <input class="fbn-color-pick" type="color" value="${hex}"
                   aria-label="${escapeHtml(label)}">
          </div>
        </div>`;
    }).join("");

    container.querySelectorAll(".fbn-color-row").forEach((row) => {
      const key = row.dataset.key;
      const text = row.querySelector(".fbn-color-text");
      const pick = row.querySelector(".fbn-color-pick");

      text.addEventListener("focus", () => {
        this._focusedColorKey = key;
      });
      text.addEventListener("blur", () => {
        if (this._focusedColorKey === key) this._focusedColorKey = null;
      });
      text.addEventListener("change", () => this._setColor(key, text.value));
      pick.addEventListener("change", () => this._setColor(key, pick.value));
    });

    // Fokus nach einem externen Neuzeichnen zurueckgeben.
    if (this._focusedColorKey) {
      const field = container.querySelector(
        `.fbn-color-row[data-key="${this._focusedColorKey}"] .fbn-color-text`
      );
      if (field) {
        const end = field.value.length;
        field.focus();
        field.setSelectionRange(end, end);
      }
    }
  }

  _setColor(key, value) {
    const config = { ...this._config, [key]: value || "" };
    this._config = config;
    this._fire(config);
    this._renderColors();
  }

  _styles() {
    return `
      .fbn-editor { display: flex; flex-direction: column; gap: 16px; }
      .fbn-color-editor {
        border: 1px solid var(--divider-color); border-radius: 6px; padding: 0;
      }
      .fbn-color-editor > summary {
        display: flex; align-items: center; gap: 8px; cursor: pointer;
        padding: 12px 16px; font-size: 16px; font-weight: 400;
        list-style: none;
      }
      .fbn-color-editor > summary::-webkit-details-marker { display: none; }
      .fbn-color-editor > summary::marker { content: ""; }
      .fbn-color-editor > summary ha-icon { --mdc-icon-size: 24px; width: 24px; height: 24px; }
      .fbn-color-title { flex: 1; }
      .fbn-color-chevron { transition: transform 180ms ease; }
      .fbn-color-editor[open] > summary .fbn-color-chevron { transform: rotate(180deg); }
      .fbn-color-body { padding: 0 16px 16px; }
      .fbn-reset {
        display: inline-flex; align-items: center; gap: 6px;
        border: 1px solid var(--divider-color); border-radius: 4px;
        background: none; color: var(--primary-color); font: inherit;
        font-size: 0.9em; padding: 6px 12px; cursor: pointer; margin-bottom: 12px;
      }
      .fbn-reset ha-icon { --mdc-icon-size: 18px; width: 18px; height: 18px; }
      .fbn-color-row {
        display: flex; align-items: center; justify-content: space-between;
        gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--divider-color);
        flex-wrap: wrap;
      }
      .fbn-color-row:last-child { border-bottom: none; }
      .fbn-color-meta { display: flex; flex-direction: column; min-width: 140px; }
      .fbn-color-note { font-size: 0.75em; color: var(--secondary-text-color); }
      .fbn-invalid { font-size: 0.75em; color: var(--error-color); }
      .fbn-color-controls { display: flex; align-items: center; gap: 8px; }
      .fbn-color-preview {
        width: 22px; height: 22px; border-radius: 4px;
        border: 1px solid var(--divider-color); flex: 0 0 auto;
      }
      .fbn-color-text {
        width: 120px; padding: 4px 6px; font: inherit; font-size: 0.9em;
        border: 1px solid var(--divider-color); border-radius: 4px;
        background: none; color: var(--primary-text-color);
      }
      .fbn-color-pick {
        width: 34px; height: 28px; padding: 0; border: none; background: none;
        cursor: pointer;
      }
    `;
  }
}

/* ------------------------------------------------------------------ */
/* Registrierung                                                       */
/* ------------------------------------------------------------------ */

if (!customElements.get("fritzbox-netzwerk-card")) {
  customElements.define("fritzbox-netzwerk-card", FritzboxNetzwerkCard);
}
if (!customElements.get("fritzbox-netzwerk-card-editor")) {
  customElements.define("fritzbox-netzwerk-card-editor", FritzboxNetzwerkCardEditor);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "fritzbox-netzwerk-card")) {
  window.customCards.push({
    type: "fritzbox-netzwerk-card",
    name: "FRITZ!Box Netzwerk",
    description: "Sortierbare Tabelle aller Geräte im FRITZ!Box-Heimnetz.",
    preview: false,
    documentationURL: "https://github.com/Meine-smarte-Welt/fritzbox_netzwerk",
  });
}

console.info(
  `%c FRITZBOX-NETZWERK-CARD %c ${FBN_VERSION} `,
  "color:#fff;background:#1c6ea4;font-weight:700;",
  "color:#1c6ea4;background:#fff;font-weight:700;"
);
