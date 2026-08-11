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

const FBN_VERSION = "0.1.0";

/* ------------------------------------------------------------------ */
/* Konfiguration                                                       */
/* ------------------------------------------------------------------ */

const CONFIG_DEFAULTS = {
  entity: "",
  title: "Netzwerkgeräte",

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

  // Darstellung
  show_summary: true,
  show_search: true,
  show_filter: true,
  hide_inactive: false,
  compact: false,
  max_rows: 0,
  open_device_on_click: true,

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
];

const FILTERS = [
  { key: "alle", label: "Alle", icon: "mdi:format-list-bulleted" },
  { key: "aktiv", label: "Aktiv", icon: "mdi:lan-connect" },
  { key: "inaktiv", label: "Inaktiv", icon: "mdi:lan-disconnect" },
  { key: "gast", label: "Gast", icon: "mdi:account-question" },
  { key: "gesperrt", label: "Gesperrt", icon: "mdi:web-off" },
  { key: "update", label: "Update", icon: "mdi:package-down" },
];

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

/** Restlaufzeit der DHCP-Zuweisung in lesbarer Form. */
function formatLease(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value) || value <= 0) return "";
  if (value < 3600) return `noch ${Math.round(value / 60)} min`;
  if (value < 86400) return `noch ${Math.round(value / 3600)} h`;
  return `noch ${Math.round(value / 86400)} Tage`;
}

/** Icon je Verbindungsart. */
function connectionIcon(host) {
  if (!host.active) return "mdi:lan-disconnect";
  if (host.connection === "wlan") return "mdi:wifi";
  if (host.connection === "lan") return "mdi:ethernet";
  if (host.connection === "powerline") return "mdi:power-plug";
  return "mdi:help-network-outline";
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
    case "ip_type":
      if (host.static_ip === true) return "0";
      if (host.static_ip === false) return "1";
      return "2";
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
    this._sortBy = "ip";
    this._sortDir = "asc";
    this._signature = "";
    this._built = false;
    this._resizeObserver = null;
  }

  /* -- Lovelace-Schnittstelle -------------------------------------- */

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Bitte den Sensor mit der Geräteliste auswählen (entity).");
    }
    this._config = withDefaults(config);
    this._sortBy = this._config.sort_by;
    this._sortDir = this._config.sort_dir === "desc" ? "desc" : "asc";
    this._built = false;
    this._signature = "";
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
    const hosts = this._hosts();
    const signature = this._computeSignature(hosts);
    const changed = signature !== this._signature;
    this._signature = signature;
    this._renderSummary();
    this._renderBody();
    if (changed) this._renderHead();
  }

  _build() {
    const config = this._config;
    this.innerHTML = "";

    const card = document.createElement("ha-card");
    card.className = "fbn-card";
    if (config.title) card.setAttribute("header", config.title);
    card.innerHTML = `
      <style>${this._styles()}</style>
      <div class="fbn-root${config.compact ? " fbn-compact" : ""}">
        <div class="fbn-toolbar">
          <div class="fbn-filters"></div>
          <div class="fbn-searchwrap"></div>
        </div>
        <div class="fbn-summary"></div>
        <div class="fbn-scroll">
          <table class="fbn-table">
            <thead><tr class="fbn-head"></tr></thead>
            <tbody class="fbn-body"></tbody>
          </table>
        </div>
        <div class="fbn-empty" hidden>Keine Geräte gefunden.</div>
      </div>
    `;
    this.appendChild(card);

    this._root = card.querySelector(".fbn-root");
    this._root.style.cssText = this._colorVars();

    this._buildFilters();
    this._buildSearch();
    this._buildHead();
    this._renderHead();
    this._observeWidth();
  }

  _buildFilters() {
    const container = this.querySelector(".fbn-filters");
    if (!container) return;
    if (!this._config.show_filter) {
      container.hidden = true;
      return;
    }
    container.innerHTML = FILTERS.map(
      (filter) => `
        <button class="fbn-chip" data-filter="${filter.key}" type="button"
                aria-pressed="${filter.key === this._filter}">
          <ha-icon icon="${filter.icon}"></ha-icon><span>${escapeHtml(filter.label)}</span>
        </button>`
    ).join("");
    container.addEventListener("click", (event) => {
      const button = event.target.closest(".fbn-chip");
      if (!button) return;
      this._filter = button.dataset.filter;
      container.querySelectorAll(".fbn-chip").forEach((chip) => {
        chip.setAttribute("aria-pressed", String(chip.dataset.filter === this._filter));
      });
      this._renderSummary();
      this._renderBody();
    });
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
        <input type="search" placeholder="Name, IP oder MAC" aria-label="Geräte durchsuchen">
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
        const label = column.key === "status" ? "Status" : column.label;
        return `
          <th class="fbn-th fbn-col-${column.key} fbn-prio-${column.prio}"
              data-sort="${column.key}" scope="col" tabindex="0" role="columnheader"
              style="text-align:${column.align || "left"}"
              title="Nach ${escapeHtml(label)} sortieren">
            <span class="fbn-th-inner">
              <span class="fbn-th-label">${escapeHtml(column.label)}</span>
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
      `${attributes.gesamt || 0} Geräte`,
      `${attributes.aktiv || 0} aktiv`,
    ];
    if (attributes.updates_verfuegbar) {
      parts.push(`${attributes.updates_verfuegbar} mit Update`);
    }
    if (attributes.gesperrt) parts.push(`${attributes.gesperrt} gesperrt`);
    const filtered = shown !== (attributes.gesamt || 0) ? ` · ${shown} angezeigt` : "";
    container.textContent = parts.join(" · ") + filtered;
  }

  _renderBody() {
    const body = this.querySelector(".fbn-body");
    const empty = this.querySelector(".fbn-empty");
    if (!body) return;

    const state = this._stateObj();
    if (!state) {
      body.innerHTML = "";
      if (empty) {
        empty.hidden = false;
        empty.textContent = `Der Sensor ${this._config.entity} ist nicht verfügbar.`;
      }
      return;
    }

    const hosts = this._filteredHosts();
    if (empty) {
      empty.hidden = hosts.length > 0;
      empty.textContent = "Keine Geräte gefunden.";
    }

    const columns = this._visibleColumns();
    body.innerHTML = hosts
      .map((host) => this._renderRow(host, columns))
      .join("");

    if (!body.dataset.bound) {
      body.dataset.bound = "1";
      body.addEventListener("click", (event) => {
        const row = event.target.closest("tr[data-device]");
        if (!row || !this._config.open_device_on_click) return;
        this._openDevice(row.dataset.device);
      });
    }
  }

  _renderRow(host, columns) {
    const deviceAttr = host.ha_device_id
      ? ` data-device="${escapeHtml(host.ha_device_id)}"`
      : "";
    const classes = ["fbn-tr"];
    if (!host.active) classes.push("fbn-inactive");
    if (host.ha_device_id && this._config.open_device_on_click) {
      classes.push("fbn-clickable");
    }
    const cells = columns
      .map(
        (column) =>
          `<td class="fbn-td fbn-col-${column.key} fbn-prio-${column.prio}" style="text-align:${
            column.align || "left"
          }">${this._renderCell(host, column.key)}</td>`
      )
      .join("");
    return `<tr class="${classes.join(" ")}"${deviceAttr}>${cells}</tr>`;
  }

  _renderCell(host, key) {
    switch (key) {
      case "status":
        return `<span class="fbn-dot ${
          host.active ? "fbn-dot-on" : "fbn-dot-off"
        }" title="${host.active ? "Verbunden" : "Nicht verbunden"}"></span>`;

      case "name": {
        const badges = [];
        if (host.guest) badges.push('<span class="fbn-badge fbn-badge-guest">Gast</span>');
        if (host.vpn) badges.push('<span class="fbn-badge">VPN</span>');
        if (host.priority) badges.push('<span class="fbn-badge">Priorität</span>');
        return `
          <div class="fbn-namecell">
            <ha-icon class="fbn-rowicon" icon="${connectionIcon(host)}"></ha-icon>
            <span class="fbn-name">${escapeHtml(host.name)}</span>
            ${badges.join("")}
          </div>`;
      }

      case "ip":
        return `<span class="fbn-mono">${escapeHtml(host.ip || "—")}</span>`;

      case "mac":
        return `<span class="fbn-mono fbn-dim">${escapeHtml(host.mac || "—")}</span>`;

      case "connection":
        return escapeHtml(host.connection_label || "—");

      case "ha_name":
        return host.ha_name
          ? `<span class="fbn-ha">${escapeHtml(host.ha_name)}</span>`
          : '<span class="fbn-dim">—</span>';

      case "ip_type": {
        if (host.static_ip === true) {
          return '<span class="fbn-badge fbn-badge-static">statisch</span>';
        }
        if (host.static_ip === false) {
          const lease = formatLease(host.lease_time_remaining);
          return `<span class="fbn-dim">DHCP${
            lease ? ` <span class="fbn-lease">(${escapeHtml(lease)})</span>` : ""
          }</span>`;
        }
        return '<span class="fbn-dim" title="IP-Typ-Erfassung ist ausgeschaltet oder noch nicht gelaufen">—</span>';
      }

      case "wan":
        return host.blocked
          ? '<ha-icon class="fbn-icon-blocked" icon="mdi:web-off" title="Internetzugang gesperrt"></ha-icon>'
          : '<span class="fbn-dim">—</span>';

      case "update":
        return host.update_available
          ? '<ha-icon class="fbn-icon-update" icon="mdi:package-down" title="Firmware-Update verfügbar"></ha-icon>'
          : '<span class="fbn-dim">—</span>';

      case "speed":
        return `<span class="fbn-mono fbn-dim">${escapeHtml(formatSpeed(host.speed))}</span>`;

      case "model":
        return escapeHtml(host.model || "—");

      case "type":
        return escapeHtml(host.device_class_user || host.device_class || "—");

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

  /* -- Breite ------------------------------------------------------- */

  /**
   * Blendet Spalten geringerer Prioritaet aus, sobald die Karte schmal
   * wird. Bewusst ueber eine Klasse am Wurzelelement statt ueber Media
   * Queries: die Karte kann in einer schmalen Spalte eines breiten
   * Bildschirms stehen, dann greifen Media Queries am Fenster nicht.
   */
  _observeWidth() {
    if (this._resizeObserver || typeof ResizeObserver === "undefined") return;
    if (!this._root) return;
    this._resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const width = entry.contentRect.width;
        this._root.classList.toggle("fbn-narrow", width < 620);
        this._root.classList.toggle("fbn-xnarrow", width < 420);
      }
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
      .fbn-scroll { overflow-x: auto; }
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
      .fbn-namecell { display: flex; align-items: center; gap: 6px; min-width: 0; }
      .fbn-rowicon { --mdc-icon-size: 18px; width: 18px; height: 18px; flex: 0 0 auto; }
      .fbn-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .fbn-mono { font-family: var(--code-font-family, monospace); font-size: 0.95em; }
      .fbn-dim { color: var(--fbn-inactive); }
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
      .fbn-narrow .fbn-prio-3 { display: none; }
      .fbn-xnarrow .fbn-prio-2 { display: none; }
      @media (prefers-reduced-motion: no-preference) {
        .fbn-chip, .fbn-tr { transition: color 120ms ease, background 120ms ease; }
      }
    `;
  }
}

/* ------------------------------------------------------------------ */
/* Editor                                                              */
/* ------------------------------------------------------------------ */

const EDITOR_SCHEMA = [
  { name: "entity", required: true, selector: { entity: { domain: "sensor" } } },
  { name: "title", selector: { text: {} } },
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
      { name: "hide_inactive", selector: { boolean: {} } },
      { name: "compact", selector: { boolean: {} } },
      { name: "open_device_on_click", selector: { boolean: {} } },
      {
        name: "max_rows",
        selector: { number: { min: 0, max: 500, mode: "box" } },
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
  show_status: "Status",
  show_name: "Gerät",
  show_ip: "IP-Adresse",
  show_mac: "MAC-Adresse",
  show_connection: "Verbindung",
  show_ha_name: "Home-Assistant-Gerätename",
  show_ip_type: "IP-Typ (DHCP oder statisch)",
  show_wan: "Internetzugang",
  show_update: "Firmware-Update",
  show_speed: "Tempo",
  show_model: "Modell",
  show_type: "Gerätetyp",
  show_summary: "Zusammenfassung anzeigen",
  show_search: "Suchfeld anzeigen",
  show_filter: "Filterleiste anzeigen",
  hide_inactive: "Nicht verbundene Geräte ausblenden",
  compact: "Kompakte Zeilen",
  open_device_on_click: "Klick öffnet das Home-Assistant-Gerät",
  max_rows: "Höchstzahl Zeilen (0 = alle)",
  sort_by: "Sortieren nach",
  sort_dir: "Richtung",
};

const EDITOR_HELPERS = {
  show_ip_type: "Braucht die eingeschaltete IP-Typ-Erfassung in den Einstellungen der Integration.",
  show_ha_name: "Zeigt den Gerätenamen aus Home Assistant, sofern das Gerät dort eine MAC-Adresse hinterlegt hat.",
  max_rows: "Begrenzt die Tabelle, zum Beispiel für eine Übersichtskarte.",
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
  }

  set hass(hass) {
    this._hass = hass;
    if (this._form) this._form.hass = hass;
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
              <ha-icon icon="mdi:palette"></ha-icon>
              <span class="fbn-color-title">Farben</span>
              <ha-icon class="fbn-color-chevron" icon="mdi:chevron-down"></ha-icon>
            </summary>
            <div class="fbn-color-body">
              <button type="button" class="fbn-reset">Alle Farben zurücksetzen</button>
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
      const note = safe
        ? `aktuell: ${escapeHtml(safe)}`
        : `aktuell: Standard des Themes (${escapeHtml(COLOR_FALLBACKS[field.key])})`;
      const invalid = raw && !safe ? '<span class="fbn-invalid">Wert nicht gültig</span>' : "";
      return `
        <div class="fbn-color-row" data-key="${field.key}">
          <div class="fbn-color-meta">
            <span class="fbn-color-label">${escapeHtml(field.label)}</span>
            <span class="fbn-color-note">${note}</span>
            ${invalid}
          </div>
          <div class="fbn-color-controls">
            <span class="fbn-color-preview" style="background:${effective}"></span>
            <input class="fbn-color-text" type="text" value="${escapeHtml(raw)}"
                   placeholder="z. B. #4caf50" aria-label="${escapeHtml(field.label)}">
            <input class="fbn-color-pick" type="color" value="${hex}"
                   aria-label="${escapeHtml(field.label)} grafisch wählen">
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
        border: 1px solid var(--divider-color); border-radius: 4px;
        background: none; color: var(--primary-color); font: inherit;
        font-size: 0.9em; padding: 6px 12px; cursor: pointer; margin-bottom: 12px;
      }
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
