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

const FBN_VERSION = "1.5.2b0";

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

  // Darstellung
  show_summary: true,
  show_search: true,
  show_filter: true,
  show_controls: false,
  show_tabs: false,
  // Einzelne Filter-Buttons an/aus (nur wirksam, wenn show_filter an ist).
  filter_alle: true,
  filter_aktiv: true,
  filter_inaktiv: true,
  filter_gast: true,
  filter_gesperrt: true,
  filter_update: true,
  // Welcher Filter beim Laden/Neuöffnen aktiv ist.
  default_filter: "alle",
  hide_inactive: false,
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
  { key: "connection", cfg: "show_connection", label: "Verbindung", prio: 2, sortable: true },
  { key: "ha_name", cfg: "show_ha_name", label: "Home Assistant", prio: 2, sortable: true },
  { key: "ip_type", cfg: "show_ip_type", label: "IP-Typ", prio: 3, sortable: true },
  { key: "wan", cfg: "show_wan", label: "Internet", prio: 3, sortable: true, align: "center" },
  { key: "update", cfg: "show_update", label: "Update", prio: 3, sortable: true, align: "center" },
  { key: "speed", cfg: "show_speed", label: "Tempo", prio: 3, sortable: true, align: "right" },
  { key: "model", cfg: "show_model", label: "Modell", prio: 3, sortable: true },
  { key: "type", cfg: "show_type", label: "Gerätetyp", prio: 3, sortable: true },
  { key: "last_seen", cfg: "show_last_seen", label: "Zuletzt online", prio: 3, sortable: true },
];

const FILTERS = [
  { key: "alle", label: "Alle", icon: "mdi:format-list-bulleted" },
  { key: "aktiv", label: "Aktiv", icon: "mdi:lan-connect" },
  { key: "inaktiv", label: "Inaktiv", icon: "mdi:lan-disconnect" },
  { key: "gast", label: "Gast", icon: "mdi:account-question" },
  { key: "gesperrt", label: "Gesperrt", icon: "mdi:web-off" },
  { key: "update", label: "Update", icon: "mdi:package-down" },
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
    "col.last_seen": "Zuletzt online", "col.status": "Status",
    "flt.alle": "Alle", "flt.aktiv": "Aktiv", "flt.inaktiv": "Inaktiv",
    "flt.gast": "Gast", "flt.gesperrt": "Gesperrt", "flt.update": "Update",
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
    "ctl.throughput": "Aktueller Durchsatz (Download / Upload)", "ctl.wlan_24": "WLAN 2,4 GHz", "ctl.wlan_5": "WLAN 5 GHz", "ctl.wlan_guest": "Gast-WLAN", "ctl.reconnect": "Neu verbinden", "ctl.reboot": "Neustart", "ctl.reboot_confirm": "Wirklich neu starten?",
    "field.tracker": "Anwesenheit", "tracker.home": "zuhause", "tracker.away": "abwesend", "tracker.open": "Tracker öffnen",
    "tracker.unknown": "unbekannt", "tracker.disabled": "Entität deaktiviert",
    "tracker.disabled_hint": "Die Tracker-Entität ist in Home Assistant deaktiviert – hier klicken und im Zahnrad-Dialog aktivieren.",
    "tracker.off": "nicht aktiviert",
    "tracker.off_hint": "Device Tracker einschalten unter: Einstellungen → Geräte & Dienste → FRITZ!Box Netzwerk → Konfigurieren.", "tab.network": "Netzwerk", "tab.controls": "Steuerung",
  },
  en: {
    "col.name": "Device", "col.ip": "IP address", "col.mac": "MAC address",
    "col.connection": "Connection", "col.ha_name": "Home Assistant",
    "col.ip_type": "IP type", "col.wan": "Internet", "col.update": "Update",
    "col.speed": "Speed", "col.model": "Model", "col.type": "Device type",
    "col.last_seen": "Last seen", "col.status": "Status",
    "flt.alle": "All", "flt.aktiv": "Active", "flt.inaktiv": "Inactive",
    "flt.gast": "Guest", "flt.gesperrt": "Blocked", "flt.update": "Update",
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
    "ctl.throughput": "Current throughput (download / upload)", "ctl.wlan_24": "Wi-Fi 2.4 GHz", "ctl.wlan_5": "Wi-Fi 5 GHz", "ctl.wlan_guest": "Guest Wi-Fi", "ctl.reconnect": "Reconnect", "ctl.reboot": "Reboot", "ctl.reboot_confirm": "Really reboot?",
    "field.tracker": "Presence", "tracker.home": "home", "tracker.away": "away", "tracker.open": "Open tracker",
    "tracker.unknown": "unknown", "tracker.disabled": "entity disabled",
    "tracker.disabled_hint": "The tracker entity is disabled in Home Assistant – click here and enable it in the settings dialog.",
    "tracker.off": "not enabled",
    "tracker.off_hint": "Enable the device tracker under: Settings → Devices & services → FRITZ!Box Netzwerk → Configure.", "tab.network": "Network", "tab.controls": "Controls",
  },
  nl: {
    "col.name": "Apparaat", "col.ip": "IP-adres", "col.mac": "MAC-adres",
    "col.connection": "Verbinding", "col.ha_name": "Home Assistant",
    "col.ip_type": "IP-type", "col.wan": "Internet", "col.update": "Update",
    "col.speed": "Snelheid", "col.model": "Model", "col.type": "Apparaattype",
    "col.last_seen": "Laatst online", "col.status": "Status",
    "flt.alle": "Alle", "flt.aktiv": "Actief", "flt.inaktiv": "Inactief",
    "flt.gast": "Gast", "flt.gesperrt": "Geblokkeerd", "flt.update": "Update",
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
    "ctl.throughput": "Huidige doorvoer (download / upload)", "ctl.wlan_24": "Wifi 2,4 GHz", "ctl.wlan_5": "Wifi 5 GHz", "ctl.wlan_guest": "Gast-wifi", "ctl.reconnect": "Opnieuw verbinden", "ctl.reboot": "Herstart", "ctl.reboot_confirm": "Echt herstarten?",
    "field.tracker": "Aanwezigheid", "tracker.home": "thuis", "tracker.away": "afwezig", "tracker.open": "Tracker openen",
    "tracker.unknown": "onbekend", "tracker.disabled": "entiteit uitgeschakeld",
    "tracker.disabled_hint": "De trackerentiteit is uitgeschakeld in Home Assistant – klik hier en schakel deze in via het instellingenvenster.",
    "tracker.off": "niet ingeschakeld",
    "tracker.off_hint": "Device tracker inschakelen via: Instellingen → Apparaten & diensten → FRITZ!Box Netzwerk → Configureren.", "tab.network": "Netwerk", "tab.controls": "Bediening",
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
    case "connection":
      return String(host.connection_label || "").toLowerCase();
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
/* Karte                                                               */
/* ------------------------------------------------------------------ */

class FritzboxNetzwerkCard extends HTMLElement {
  constructor() {
    super();
    this._config = withDefaults({});
    this._hass = null;
    this._search = "";
    this._filter = "alle";
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
    this._built = false;
    this._signature = "";
    this._renderedOnce = false;
    this._lastStateObj = null;
    this._closePopup();
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
    const entity = Object.keys(hass && hass.states ? hass.states : {}).find(
      (id) => id.startsWith("sensor.") && id.includes("gerate")
    );
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
  }

  /* -- Daten -------------------------------------------------------- */

  _stateObj() {
    if (!this._hass || !this._config.entity) return null;
    return this._hass.states[this._config.entity] || null;
  }

  _hosts() {
    const state = this._stateObj();
    if (!state || !state.attributes) return [];
    const hosts = state.attributes.hosts;
    return Array.isArray(hosts) ? hosts : [];
  }

  /** Erkennt, ob sich an den angezeigten Daten ueberhaupt etwas geaendert hat. */
  _computeSignature(hosts) {
    return hosts
      .map((host) =>
        [
          host.mac,
          host.ip,
          host.name,
          host.active ? 1 : 0,
          host.connection_label,
          host.ha_name,
          host.static_ip,
          host.blocked ? 1 : 0,
          host.update_available ? 1 : 0,
          host.speed,
        ].join("|")
      )
      .join("~");
  }

  _visibleColumns() {
    return COLUMNS.filter((column) => this._config[column.cfg]);
  }

  _filteredHosts() {
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
      default:
        break;
    }

    if (search) {
      hosts = hosts.filter((host) =>
        [host.name, host.ip, host.mac, host.ha_name, host.model, host.host_name]
          .map((value) => String(value || "").toLowerCase())
          .some((value) => value.includes(search))
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
    this._renderSummary();
    this._renderBody();
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
    const attributes = (state && state.attributes) || {};
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
  _renderControls() {
    const box = this.querySelector(".fbn-controls");
    if (!box) return;
    const state = this._stateObj();
    const attributes = (state && state.attributes) || {};
    const connection = attributes.connection || null;
    const controls = attributes.controls || null;

    // Ohne Schalter (Einstellung aus) und ohne Verbindungsdaten: leeren.
    if (!this._config.show_controls || (!connection && !controls)) {
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
    }
    if (controls && controls.reconnect) {
      parts.push(`
        <button class="fbn-ctl-btn fbn-ctl-reconnect" type="button"
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
    box.innerHTML = parts.join("");

    if (!box.dataset.bound) {
      box.dataset.bound = "1";
      box.addEventListener("click", (event) => this._onControlClick(event));
    }
    this._applyTabs();
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
    const reconnect = event.target.closest(".fbn-ctl-reconnect");
    if (reconnect) {
      this._pressButton(reconnect);
      return;
    }
    const reboot = event.target.closest(".fbn-ctl-reboot");
    if (reboot) {
      // Zwei-Klick-Bestaetigung: der erste Klick "schaerft" den Button.
      if (reboot.dataset.armed !== "1") {
        reboot.dataset.armed = "1";
        reboot.classList.add("fbn-ctl-armed");
        reboot.querySelector("span").textContent = this._t("ctl.reboot_confirm");
        clearTimeout(this._rebootTimer);
        this._rebootTimer = setTimeout(() => {
          reboot.dataset.armed = "0";
          reboot.classList.remove("fbn-ctl-armed");
          const span = reboot.querySelector("span");
          if (span) span.textContent = this._t("ctl.reboot");
        }, 4000);
        return;
      }
      clearTimeout(this._rebootTimer);
      this._pressButton(reboot);
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
    body.innerHTML = hosts
      .map((host) => this._renderRow(host, columns))
      .join("");

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

      case "mac":
        return `<span class="fbn-mono fbn-dim">${escapeHtml(host.mac || "—")}</span>`;

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

    // Schliessen in der Fusszeile.
    const footClose = this._popup.querySelector(".fbn-modal-close2");
    if (footClose) footClose.addEventListener("click", () => this._closePopup());
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

    add(this._t("field.name"), escapeHtml(host.name));
    add(this._t("col.ip"), escapeHtml(host.ip), { mono: true, copy: host.ip });
    add(this._t("col.mac"), escapeHtml(host.mac), { mono: true, copy: host.mac });
    add(this._t("col.connection"), escapeHtml(this._connLabel(host)));
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

    // Device Tracker: seit 1.5.2b0 immer als eigene Zeile - mit dem echten
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

  /** Kopiert einen Wert in die Zwischenablage, mit kurzer Rueckmeldung. */
  _copy(value, button) {
    const done = () => {
      const icon = button.querySelector("ha-icon");
      if (icon) icon.setAttribute("icon", "mdi:check");
      setTimeout(() => {
        if (icon) icon.setAttribute("icon", "mdi:content-copy");
      }, 1200);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(value).then(done).catch(() => {});
    }
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
    const returnTo = this._popupReturnFocus;
    this._popupReturnFocus = null;
    if (returnTo && returnTo.focus && document.contains(returnTo)) {
      returnTo.focus();
    }
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
      .fbn-ctl-chip, .fbn-ctl-btn {
        display: inline-flex; align-items: center; gap: 5px;
        border: 1px solid var(--fbn-border); border-radius: 16px;
        background: none; color: inherit; cursor: pointer;
        padding: 4px 12px; font: inherit; font-size: 0.85em; line-height: 1.4;
      }
      .fbn-ctl-chip ha-icon, .fbn-ctl-btn ha-icon {
        --mdc-icon-size: 16px; width: 16px; height: 16px;
      }
      .fbn-ctl-wlan[aria-pressed="true"] {
        border-color: var(--fbn-active); color: var(--fbn-active);
      }
      .fbn-ctl-wlan[aria-pressed="false"] { opacity: 0.6; }
      .fbn-ctl-btn:hover, .fbn-ctl-chip:hover { background: var(--fbn-header-bg); }
      .fbn-ctl-btn[disabled] { opacity: 0.6; cursor: default; }
      .fbn-ctl-armed {
        border-color: var(--fbn-blocked); color: var(--fbn-blocked);
        font-weight: 600;
      }
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
      { name: "show_tabs", selector: { boolean: {} } },
      { name: "hide_inactive", selector: { boolean: {} } },
      { name: "compact", selector: { boolean: {} } },
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
  show_summary: "Zusammenfassung anzeigen",
  show_search: "Suchfeld anzeigen",
  show_filter: "Filterleiste anzeigen",
  show_controls: "Steuerungsleiste anzeigen",
  show_tabs: "Kategorien als Tabs anzeigen",
  filter_alle: "Button „Alle“",
  filter_aktiv: "Button „Aktiv“",
  filter_inaktiv: "Button „Inaktiv“",
  filter_gast: "Button „Gast“",
  filter_gesperrt: "Button „Gesperrt“",
  filter_update: "Button „Update“",
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
  show_controls: "Zeigt in der Karte eine Leiste mit Live-Down/Up sowie – wenn die FRITZ!Box-Steuerung in den Integrationseinstellungen aktiviert ist – WLAN-Schaltern und den Buttons Neuverbinden/Neustart.",
  default_filter: "Welcher Filter aktiv ist, wenn die Karte geladen oder neu geöffnet wird (z. B. „Aktiv“). Nach einem Refresh wird nicht mehr auf „Alle“ zurückgesetzt.",
  language: "Sprache der Beschriftungen in der Karte. „Automatisch“ folgt der in Home Assistant eingestellten Sprache (Deutsch, Englisch, Niederländisch).",
  show_title: "Blendet die Kopfzeile der Karte aus, z. B. für ein Popup oder eine kompakte Ansicht.",
  show_ip_type: "Braucht die eingeschaltete IP-Typ-Erfassung in den Einstellungen der Integration.",
  show_ha_name: "Zeigt den Gerätenamen aus Home Assistant, sofern das Gerät dort eine MAC-Adresse hinterlegt hat. Ein Klick auf den Namen führt direkt zum Gerät.",
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
    show_status: "Status", show_name: "Device", show_ip: "IP address",
    show_mac: "MAC address", show_connection: "Connection",
    show_ha_name: "Home Assistant device name (linked)",
    show_ip_type: "IP type (DHCP or static)", show_wan: "Internet access",
    show_update: "Firmware update", show_speed: "Speed", show_model: "Model",
    show_type: "Device type", show_last_seen: "Last seen",
    show_summary: "Show summary", show_search: "Show search field",
    show_filter: "Show filter bar",
    show_controls: "Show controls bar",
    show_tabs: "Show categories as tabs",
    help_show_tabs: "Shows tabs for the Network and Controls categories at the top. Each tab shows only its own elements: Network the filters, search and device list, Controls the download/upload display, Wi-Fi switches and reconnect/reboot. The Controls tab only appears when the controls bar is enabled. Without tabs, both areas appear below each other as before.",
    help_show_controls: "Shows a bar with live download/upload and \u2013 if FRITZ!Box controls are enabled in the integration settings \u2013 Wi-Fi switches and reconnect/reboot buttons.",
    filter_alle: '"All" button', filter_aktiv: '"Active" button',
    filter_inaktiv: '"Inactive" button', filter_gast: '"Guest" button',
    filter_gesperrt: '"Blocked" button', filter_update: '"Update" button',
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
    color_cat_alle: "Icon category \"All\"", color_cat_aktiv: "Icon category \"Active\"", color_cat_inaktiv: "Icon category \"Inactive\"", color_cat_gast: "Icon category \"Guest\"", color_cat_gesperrt: "Icon category \"Blocked\"", color_cat_update: "Icon category \"Update\"",
  },
  nl: {
    entity: "Sensor met de apparaatlijst", title: "Titel", show_title: "Titel tonen",
    language: "Taal van de kaart",
    show_status: "Status", show_name: "Apparaat", show_ip: "IP-adres",
    show_mac: "MAC-adres", show_connection: "Verbinding",
    show_ha_name: "Home Assistant-apparaatnaam (gelinkt)",
    show_ip_type: "IP-type (DHCP of statisch)", show_wan: "Internettoegang",
    show_update: "Firmware-update", show_speed: "Snelheid", show_model: "Model",
    show_type: "Apparaattype", show_last_seen: "Laatst online",
    show_summary: "Samenvatting tonen", show_search: "Zoekveld tonen",
    show_filter: "Filterbalk tonen",
    show_controls: "Bedieningsbalk tonen",
    show_tabs: "Categorieën als tabs tonen",
    help_show_tabs: "Toont bovenaan tabs voor de categorieën Netwerk en Bediening. Elke tab toont uitsluitend de eigen elementen: Netwerk de filters, het zoekveld en de apparatenlijst, Bediening de download/upload-weergave, de wifi-schakelaars en opnieuw verbinden/herstarten. De tab Bediening verschijnt alleen als de bedieningsbalk is ingeschakeld. Zonder tabs verschijnen beide gebieden onder elkaar zoals voorheen.",
    help_show_controls: "Toont een balk met live download/upload en \u2013 als de FRITZ!Box-bediening in de integratie-instellingen is ingeschakeld \u2013 wifi-schakelaars en knoppen voor opnieuw verbinden/herstarten.",
    filter_alle: 'Knop "Alle"', filter_aktiv: 'Knop "Actief"',
    filter_inaktiv: 'Knop "Inactief"', filter_gast: 'Knop "Gast"',
    filter_gesperrt: 'Knop "Geblokkeerd"', filter_update: 'Knop "Update"',
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
    color_cat_alle: "Pictogram categorie \"Alle\"", color_cat_aktiv: "Pictogram categorie \"Actief\"", color_cat_inaktiv: "Pictogram categorie \"Inactief\"", color_cat_gast: "Pictogram categorie \"Gast\"", color_cat_gesperrt: "Pictogram categorie \"Geblokkeerd\"", color_cat_update: "Pictogram categorie \"Update\"",
  },
};

class FritzboxNetzwerkCardEditor extends HTMLElement {
  constructor() {
    super();
    this._config = withDefaults({});
    this._hass = null;
    this._rendered = false;
    this._focusedColorKey = null;
  }

  setConfig(config) {
    this._config = withDefaults(config);
    this._render();
    this._applyLanguage();
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
