**🌍 Sprache · Language · Taal · Langue · Idioma**

| 🇩🇪 [Deutsch](README.md) | 🇬🇧 **English** | 🇳🇱 [Nederlands](README.nl.md) | 🇫🇷 [Français](README.fr.md) | 🇪🇸 [Español](README.es.md) |
|:---:|:---:|:---:|:---:|:---:|

# FRITZ!Box Netzwerk

A Home Assistant integration that puts every device in the FRITZ!Box home network on your dashboard as a sortable table – with IP address, MAC address, connection type and the matching Home Assistant device name.

![Version](https://img.shields.io/badge/Version-2.0.0b5-blue)
![HACS](https://img.shields.io/badge/HACS-Custom-orange)

> This is the English edition of the README, which is available in five languages (see the language bar above). The German [README.md](README.md) is the main file and has the full card reference, the troubleshooting chapter and the complete version history. Sections marked “German only” are not translated yet. The integration and the card themselves are translated into German, English and Dutch.

---

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Setup](#setup)
- [Settings](#settings)
- [Notification Center (optional)](#notification-center-optional)
- [Sensors](#sensors)
- [Events](#events)
- [Mesh and repeaters](#mesh-and-repeaters)
- [MAC filter and pairing](#mac-filter-and-pairing)
- [Parental control: access profiles (experimental)](#parental-control-access-profiles-experimental)
- [CPU and RAM of the box (experimental)](#cpu-and-ram-of-the-box-experimental)
- [DNS settings (experimental)](#dns-settings-experimental)
- [Static IP address (experimental)](#static-ip-address-experimental)
- [The dashboard card](#the-dashboard-card)
- [Services](#services)
- [Blueprints](#blueprints)
- [Version display and update notice](#version-display-and-update-notice)
- [Languages](#languages)
- [Security](#security)
- [Known limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)
- [File integrity](#file-integrity)
- [Development and tests](#development-and-tests)
- [Version history](#version-history)
- [License](#license)

---

## Features

- All known network devices of the FRITZ!Box as **one** table on the dashboard
- **Sortable** by clicking any column header, also by keyboard; **search** over name, IP, MAC, model and Home Assistant name
- **Filter bar**: All, Active, Inactive, Guest, Blocked, Update, Fixed IP, VPN – every button can be hidden individually
- **Wi-Fi band** (2.4 / 5 GHz), **manufacturer from the MAC address** (bundled list, no internet access), **copy MAC with one click**
- **IP filter with wildcards** (`192.168.2.*`) to split a large network over several cards
- **Detail popup** per device with all fields, Wake-on-LAN, rename, label/note/“reserved” marker and a jump to the Home Assistant device
- **Last seen**, **internet access switch** (experimental), **IP type** (fixed or dynamic)
- **Connection sensors** (down/upload rate, line sync rates, external IP, online time, connection state) and **events** (“new device”, “external IP changed”)
- **Mesh group**: FRITZ!Box and repeaters as one unit, button “Restart all FRITZ! devices”
- **Wi-Fi MAC filter** on/off and temporary release (“pairing”)
- **Parental control** (experimental): switch access profiles per device, also temporarily
- **DNS settings** of the box (experimental, since 1.8.0): read and change
- **Static IP address** per device (experimental, since 1.8.0): assign with a check against duplicate addresses, button in the popup; the write path was reworked in 2.0.0 (REST interface, read-back check)
- **Reservations of the box** (since 2.0.0, untested on a box): devices with “Always assign this network device the same IPv4 address” are read from the box and counted as fixed
- **VPN devices** (since 2.0.0, untested on a box): peers the box reports with the VPN flag but without a MAC address (e.g. WireGuard) are no longer dropped from the list; the **VPN** filter button (`filter_vpn: false` hides it) shows only these devices
- **Version display and update notice** on the control page of the card
- Fully configurable through the UI incl. **free colors**, three languages (de, en, nl)

The card ships with the integration and is registered as a Lovelace resource automatically.

---

## Requirements

- Home Assistant 2024.11 or newer
- A FRITZ!Box with **“Allow access for applications”** enabled (Home Network → Network → Network Settings)
- A FRITZ!Box user with the permission **“FRITZ!Box Settings”**

---

## Installation

### Via HACS (recommended)

1. HACS → Integrations → menu top right → **Custom repositories**
2. Add `https://github.com/Meine-smarte-Welt/fritzbox_netzwerk` as category *Integration*
3. Install “FRITZ!Box Netzwerk”
4. Restart Home Assistant

**Pre-releases (beta, release candidate):** HACS only lists them if you enable **“Show beta versions”** when downloading. With a beta installed, the version display in the card also points to newer betas.

### Manually

Copy the folder `custom_components/fritzbox_netzwerk` into the `config` directory of Home Assistant and restart.

---

## Setup

Settings → Devices & services → **Add integration** → “FRITZ!Box Netzwerk”.

| Field | Meaning |
| --- | --- |
| Address | Host name or IP address, usually `fritz.box` |
| User name | FRITZ!Box user with the permission “FRITZ!Box Settings” |
| Password | The matching password |
| Encrypted connection | HTTPS instead of HTTP to the FRITZ!Box |
| Port | `0` uses the default ports; or enter your own |
| Remote access via MyFRITZ!/HTTPS | Uses HTTPS and the TR-064 path prefix `/tr064` |

The credentials are checked immediately (reachable, login valid, hosts service usable). If one fails, the dialog names the concrete cause.

For remote access enter the MyFRITZ! or DynDNS address **without protocol, port and path**, enter the HTTPS port separately and enable “Remote access via MyFRITZ!/HTTPS”. **Note:** `fritzconnection` does not verify the TLS certificate; over the open internet a VPN to your own FRITZ!Box is the safer choice (details in the German README).

---

## Settings

Via *Configure* on the integration:

| Setting | Default | Meaning |
| --- | --- | --- |
| Polling interval | 60 s | How often the device list is fetched (30–3600 s) |
| Record IP type | on | Whether DHCP/static is determined |
| IP type interval | 15 min | Cycle of the IP type collection |
| Record Wi-Fi band per device | on | Reads the connected devices per Wi-Fi network so the card can show the band |
| Create device trackers | off | One `device_tracker` per network device |
| Create repeaters as own devices | on | One Home Assistant device per AVM repeater, mesh sensor, “restart all” button |
| FRITZ!Box control (experimental) | off | Wi-Fi switch, MAC filter switch, pairing button, reconnect/restart buttons |
| Guest Wi-Fi service (since 1.9.1) | Automatic | Number (1–4) of the box's Wi-Fi service that is the guest network. “Automatic” detects it itself; only change it if the guest switch or QR code shows the wrong network |
| Check daily for a new version | on | Asks GitHub once a day for the latest version; no data about you or the box is sent |
| Control parental-control access profiles (experimental) | off | Enables the services and the profile selection in the popup |
| Change DNS settings of the box (experimental) | off | Allows `set_dns_settings` to write; reading and the preview always work |
| Set static IP address (experimental) | off | Allows `set_static_ip` and the card button to write; the preview (`dry_run`) always works |
| Read CPU and RAM of the box (experimental) | off | Three sensors from the box web interface |
| Create network devices as own devices | off | One HA device per selected device, selected by pattern |
| Send messages to the Notification Center (since 1.9.2b1) | on | Master switch for the optional connection, see [Notification Center](#notification-center-optional) |
| Message types to send (since 1.9.2b1) | all | Which message types go to the Notification Center (connection lost, monitored device offline, new device) |
| Pairing duration | 5 min | How long the MAC filter stays off during pairing (1–120 min) |

---

## Sensors

| Sensor | State | Purpose |
| --- | --- | --- |
| `sensor.<name>_gerate` | Number of connected devices | Carries the full device list in the attribute `hosts`; data source of the card |
| `sensor.<name>_gerate_mit_update` | Count | Automation “new firmware available” |
| `sensor.<name>_gesperrte_gerate` | Count | Parental-control monitoring |
| `sensor.<name>_download` / `_upload` | kB/s | Current transfer rate |
| `sensor.<name>_mesh` | Count online | FRITZ! devices reachable (box + repeaters); only with repeaters |
| `sensor.<name>_download_leitungsrate` / `_upload_leitungsrate` | Mbit/s | Maximum line sync rate |
| `sensor.<name>_externe_ip` | IPv4 address | Current public IP |
| `sensor.<name>_online_seit` | Timestamp | Since when the connection is up |
| `binary_sensor.<name>_internet_verbunden` | Connected/Not connected | Is the box online? |

If the WAN service is missing (e.g. the box runs as access point only) these sensors stay “unknown” without affecting the device list. The attribute `hosts` is excluded from the recorder.

## Events

Since 1.6.2: “new device” on first appearance in the home network and “external IP changed”, usable in automations without extra TR-064 calls.

---

## Mesh and repeaters

The FRITZ!Box and its AVM repeaters form the mesh. The integration treats them as **one group**: repeaters appear as own devices below the box, there is an online counter and the button “Restart all FRITZ! devices” (repeaters first, box last). Since 1.6.3 the card shows in “Connected via” which mesh neighbour a device uses, with the link rate. No signal strength in dBm (the mesh list does not provide it). Since 1.9.0 a device is also treated as a repeater if the box's mesh topology lists it as a mesh member, the Wi-Fi band of devices behind a repeater is read from the mesh interface name (both assumptions untested on real hardware), repeaters that only have a password (no user name) are retried with an empty user name, and the list can be grouped by mesh connection (`group_by: mesh`). Details: German README.

## MAC filter and pairing

With *FRITZ!Box control* enabled you get `switch.<name>_mac_filter` (permanently on/off) and `button.<name>_pairing_starten` (switch the filter off for the set time, then **automatically back on**). Service `set_mac_filter` and `start_pairing` do the same from automations. Experimental.

## Parental control: access profiles (experimental)

The integration **switches between existing access profiles** (Internet → Filters → Access profiles); you still create and edit them in the FRITZ!Box. Enable the option, then use the row **Access profile** in the device popup or the services `list_access_profiles`, `get_access_profile`, `set_access_profile`. With a number of minutes the profile applies only that long, then the previous one is restored. The row can be hidden with `show_parental: false`. Uses the undocumented web interface, not TR-064.

## CPU and RAM of the box (experimental)

The option “Read CPU and RAM of the box (experimental)” (off by default) creates three sensors: CPU load, RAM load, CPU temperature. They come from the web interface page `ecoStat`, not TR-064; not verified on any box – compare with System → Energy monitor.

---

## Data usage per device (experimental, since 2.0.0b2)

Option “Record data usage per device (experimental)” (off by default). It answers **which device transferred how much data over the last week**, to find devices that talk to the internet too much or overload the Wi-Fi (request from #26).

**How it works:** TR-064 provides no per-device usage figures. The integration therefore reads the box's **Online Monitor** (web interface, undocumented REST API `api/v0/monitor/…`), which provides a **data rate** per device, and integrates it over time into daily and 7-day totals (download and upload separately). The values are **estimates**, not counters from the box.

**Prerequisites and limits:**
- In the FRITZ!Box, **“Save internet data rates”** must be enabled per device (Home network → Network → device → details; “Individual devices” in the Online Monitor, FRITZ!OS 7.90/8.0 or newer). Devices without it do not appear.
- Counting starts when the option is enabled; the box does not provide past values. A full week takes 7 days.
- Totals are kept in Home Assistant storage (8 days). If Home Assistant or the polling is down for a while, that time is missing from the totals (diagnostics count the gaps under `traffic.stats`).
- **Unit unverified:** bytes per second are assumed. If the numbers look wrong, set “Unit of the online monitor values” to bits per second in the options. Diagnostics show raw sample values under `traffic.shape.sample_values` for comparison with the box's Online Monitor.

**Sensors (since 2.0.0b3):** The option creates *Data usage status* (diagnostic; shows “Data available”, “Waiting for samples”, “No data source mapped”, “No matching samples” or “Fetch error”, the reason is in the attributes), *Data usage 7 days (all devices)* and *Biggest data consumer (7 days)* (device name, top-five ranking in the attributes). Each device with values also gets *<device> Daten 7 Tage* and *<device> Daten heute* (unit bytes, shown in GB; download, upload and daily trend as attributes). Device sensors only appear once values exist for the device. **If you see nothing, look at the status sensor first.**

**In the card:** column **Data (7 days)** with a bar (click the header to sort by the biggest consumer); the popup shows “Data (7 days)” with download/upload, “Data today” and a daily trend. The column only appears when values exist; hide it with `show_traffic: false`. The CSV export contains the 7-day value in bytes.

---

## DNS settings (experimental)

Since 1.8.0 the integration reads the DNS settings of the FRITZ!Box and – only after you enable the option – can change them.

| Place in the FRITZ!Box | Service field |
| --- | --- |
| Internet → Account Information → DNS Server (IPv4) | `internet_ipv4_custom`, `internet_ipv4_dns1`, `internet_ipv4_dns2` |
| Internet → Account Information → DNS Server (IPv6) | `internet_ipv6_custom`, `internet_ipv6_dns1`, `internet_ipv6_dns2` |
| Home Network → Network → Network Settings → Advanced → IPv4 | `home_ipv4_dns` |
| Home Network → Network → Network Settings → Advanced → IPv6 | `home_ipv6_dns`, `home_ipv6_advertise` |

- `fritzbox_netzwerk.get_dns_settings` only reads and returns the values as a response.
- `fritzbox_netzwerk.set_dns_settings` changes only the fields you pass. Addresses are validated, the box is read first, checked after writing and the previous state is restored on a mismatch. If the box asks for a two-factor confirmation, nothing is changed.
- `dry_run: true` shows what would change and works without the option.

**Test status (honest):** the structure of the responses `dnscfg` and `ipv6`, the login and the write format were only **read** on a FRITZ!Box 5690 Pro. **Writing is not tested on any real box.** The REST interface (`/api/v0/generic/…`) is undocumented by AVM, not TR-064, and may change with FRITZ!OS. Wrong DNS servers can disturb name resolution in the whole home network – note the values first.

## Static IP address (experimental)

Since 1.8.0 the integration can assign a fixed IPv4 address to a device – this corresponds to *Home Network → Network → edit device → “Always assign this network device the same IPv4 address”*. Enable the option “Set static IP address (experimental)”.

- **Service:** `fritzbox_netzwerk.set_static_ip` with `mac`, `ip` and optional `dry_run: true` (preview, works without the option).
- **Button in the card:** in the device popup the row “Static IP” → *Set* → enter the address → *Check* (check only) or *Apply*. Can be hidden with `show_static_ip: false`.
- **No duplicate addresses:** the request is rejected if the address belongs to another active, fixed or “reserved”-marked device, is the box itself, lies outside the home network, is a network/broadcast address or not a valid device address. An offline device with the same address and an address inside the DHCP range only produce a warning.
- **Restart needed:** the new address applies only after the device has been restarted or reconnected to the network.
- **Safety net:** after writing, the state is read again (`query.lua`, otherwise REST or `edit_device`). If the assignment is not active afterwards, the service reports an error and – if it was active before – restores the previous state. An HTTP 200 alone does not count as success. If the state cannot be read back, the response says `verified: false` with a note.
- **Two-factor confirmation:** if the box asks for a confirmation, nothing is changed. A user with the extra confirmation enabled can make the box discard changes without any message – use a user without it for the integration.

**How it writes (since 2.0.0):** through the REST interface of the web interface, as a third-party project describes it for FRITZ!OS 8.25 (`jvejmelka/fritzbox-static-lease`): `PUT /api/v0/generic/landevice/landevice/<UID>` with `{"static_dhcp": "1"}`, the wanted address is added as `"ip"`. Up to 1.9.x the integration used form fields of `data.lua` that had only been *assumed* and that the box did not accept – changing the address did not work. The old path is now only a fallback if the box answers the REST request with an HTTP error (older FRITZ!OS).

**Test status (honest):** the duplicate check and the whole write flow are covered by tests against a **simulated** box. **Not** tested on a real FRITZ!Box: the `ip` field of the REST request is untested even in the third-party project, and the field names of the fallback are assumed. Many boxes keep reporting the old address until the device reconnects – the service then points that out. If it fails on your box, please open an issue with the error text and the diagnostics download.

---

## Notification Center (optional)

Since **1.9.2b1** (beta) the integration can send messages to the **Notification Center** – a separate, also optional
“Meine smarte Welt” integration that collects, sorts and delivers messages. **Without the Notification Center installed
nothing happens:** no error, no extra log entry, no extra request to the FRITZ!Box.

It reports over the Home Assistant event bus (no MQTT, no broker). The texts are sent once, when registering, in five
languages (de, en, nl, fr, es); the Notification Center picks the display language. At startup only the **initial state**
is reported (visible, no push), afterwards only state changes – no repeats.

| Message type | Urgency | Triggers when … | Closes |
| --- | --- | --- | --- |
| Connection to FRITZ!Box lost | Warning | a request to the box fails (the entities become “unavailable” at the same time) | on the next successful request |
| Monitored device offline | Info | a monitored device is no longer active in the device list | when it is active again |
| New device on the network | Info | a device appears in the home network for the first time (same trigger as the “New device” event entity) | one-off message, stays until acknowledged in the Notification Center |

**Monitored** are exactly the devices the integration already gives a “connected” status: repeaters (setting “Create
repeaters as own devices”) and the network devices selected by IP pattern (setting “Create network devices as own
devices”). All other devices only report “New device”.

**Settings** under *Configure*: a master switch “Send messages to the Notification Center” and a selection of “Message
types to send” (sorted by urgency). Off means nothing is sent, and the Notification Center closes already open messages
of that type. A change reloads the integration like any other setting. The switches exist **only in this dialog**, not in
the dashboard card.

**What the messages contain:** the device name (for “New device” also the IP address), nothing else – no credentials, no
vendor or connection details. The MAC address serves as a technical identifier so a message can be closed later; it is in
the event, not in the message text. Neither names nor addresses end up in the log or the diagnostics download; the
download only lists the switch state and how many messages per type were sent since startup.

**Limits:**

- There is deliberately **no delay of its own** and no new threshold: if the box reports a monitored device as inactive in
  one poll, the message appears and closes at the next poll in which it is active again. If that is too noisy, switch
  off the message type “Monitored device offline”.
- “New device” reports a device that appeared while Home Assistant was off as an initial state after startup (visible,
  no push). Right after setup it reports nothing – like the event entity.
- If the login fails repeatedly and Home Assistant asks for re-authentication, that is not a “connection lost” message;
  Home Assistant shows its own notice for that.
- **Test status:** checked only against a **simulated** event bus (bridge and triggers, 44 tests). **Not** against a real
  Notification Center, and not on a real FRITZ!Box or in a running Home Assistant. Beta: feedback explicitly welcome.

---

## The dashboard card

The card is shipped with the integration (`custom:fritzbox-netzwerk-card`). It has a graphical editor; every column, filter, the control bar and the popup rows can be switched on or off individually, colors are free to choose, three languages. The full reference (columns, sorting, IP filter, tabs, grouping, CSV export, guest Wi-Fi QR code, swiping on phones, colors) is in the German README.

```yaml
type: custom:fritzbox-netzwerk-card
entity: sensor.fritz_box_5690_pro_netzwerk_gerate
title: Home network
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
ip_filter: ""           # e.g. "192.168.2.*"
show_parental: true     # access profile row in the popup
show_static_ip: true    # static IP row in the popup
sort_by: ip
sort_dir: asc
```

---

## Services

If several boxes are set up, all services accept an optional field `config_entry` that selects the box.

| Service | Purpose |
| --- | --- |
| `set_device_name` | Rename a device in the box |
| `wake_on_lan` | Wake a device |
| `set_internet_access` (experimental) | Block/allow internet access of a device |
| `set_mac_filter`, `start_pairing` (experimental) | Wi-Fi MAC filter and temporary pairing |
| `reboot_mesh` (experimental) | Restart repeaters and box |
| `gast_wlan_info` | Guest Wi-Fi data (for the QR code); since 1.9.0 the guest service is detected and an optional `service` (1-4) can force it; since 1.9.1 the card passes the known number and the setting “Guest Wi-Fi service” can fix it |
| `set_device_note` | Label, note and “reserved” marker (stored in Home Assistant only) |
| `mark_devices_reserved` | Mark many devices as “reserved” by IP pattern (stored in Home Assistant only; `dry_run` previews) |
| `list_access_profiles`, `get_access_profile`, `set_access_profile` (experimental) | Parental-control profiles |
| `get_dns_settings`, `set_dns_settings` (experimental) | DNS settings of the box |
| `set_static_ip` (experimental) | Fixed IPv4 address for a device |
| `install_blueprints`, `update_oui` | Install blueprints, update the manufacturer list |

## Blueprints

The integration ships blueprints and a script; the button “Install blueprints” copies them into your Home Assistant configuration. Details: German README.

---

## Version display and update notice

The installed version is shown in the card (gear tab → app version), in the card editor and in the options dialog. If a newer release exists on GitHub (checked once a day), it is highlighted in orange with a link to the release notes.

## Languages

German, English and Dutch – in the config flow, entities, services and the card (language from Home Assistant, fallback English). The **README** is available in five languages: German, English, Dutch, French and Spanish (language bar at the top of each file).

## Security

Write actions need administrator rights; inputs are validated in the backend; texts in the card are escaped. Options for experimental write features are **off by default**, and risky actions have preview modes (`dry_run`) where possible.

---

## Known limitations

- **“Remove all unused connections” is missing** – TR-064 has no action for it.
- **Notification Center (since 1.9.2b1, beta)** is only tested against a simulated event bus, not a real Notification Center or real hardware; the switches exist only in the Configure dialog, not in the card, see [Notification Center](#notification-center-optional).
- **Static IP and DNS write access are experimental** and use the undocumented web interface of the box. Writing is not verified on any real box; the REST route for the static IP follows a third-party description for FRITZ!OS 8.25. They may break with any FRITZ!OS update.
- **DHCP reservations only partly recognised.** The box does not report reservations *inside* the DHCP range via TR-064. Since 2.0.0 the integration additionally reads them from the web interface (same cycle as the IP type, `query.lua`, otherwise `netDev`); whether your FRITZ!OS delivers the flag is untested. If not, such devices still show as “dynamic” – the diagnostics download (`reservations`) says which way worked. Alternatively mark devices by hand or in bulk (`mark_devices_reserved`).
- **Mesh only in parts:** no signal strength in dBm.
- **Data volume per device** is not provided by the box via TR-064.
- **VPN devices (issue #29), VPN button:** entries without a MAC address used to be dropped as stale; peers the box marks as VPN (flag `X_AVM-DE_VPN` or a VPN/WireGuard/IPsec interface type) and that have an IP address are now kept, with the identifier `VPN:<IP>`. They show up in the list and the counters but get no entities and none of the actions that need a MAC address (wake, block, rename, static IP). **Whether the box lists WireGuard peers this way is untested**; there is no documented interface to query them separately. The diagnostics download (`box_hosts.without_mac_samples`) shows how the box marks such entries.
- Devices are matched to Home Assistant devices only by MAC address.
- The full list is in the German README.

## Troubleshooting

German only: see the chapter “Fehlerbehebung” in [README.md](README.md#fehlerbehebung). Two notes: HACS decides itself when it shows a new release (issue #28) – use ⋮ → *Update information* on the repository in HACS; and for missing offline devices (issue #24) first check the setting “Hide disconnected devices” and the default filter of the card – until 2.0.0 that setting also emptied the “Inactive” and “Long offline” views. If devices are still missing, attach the diagnostics download and the debug log to the issue – it shows how many entries the box delivered (`box_hosts`). Logger: `custom_components.fritzbox_netzwerk`; the diagnostics download is anonymised.

## File integrity

Every `.py`, `.js` and `.yaml` file starts with a SHA-256 header over its content (from line 2). Check with `tail -n +2 file.py | sha256sum`. The hashes of the JSON files are listed in the German [README.md](README.md#datei-integrität).

## Development and tests

```bash
pip install fritzconnection==1.15.1 segno==1.6.6 pytest
python3 -m pytest -q tests
node tests/test_card_editor_title.js custom_components/fritzbox_netzwerk/www/fritzbox-netzwerk-card.js
```

The tests for 2.0.0 (`test_issue30_dns.py`, `test_static_ip.py`, `test_vpn_and_reservations.py`, with a `conftest.py` that loads the modules without Home Assistant) also come as a separate package, not in the repository. They run against a simulated FRITZ!Box.

The tests for 1.9.2b1 (`test_notification_bridge.py`, `test_nc_catalog.py`, `test_coordinator_nc.py`, `test_updates_prerelease.py`, with their own `conftest.py` that replaces Home Assistant with stubs) come with the release as a separate package, not in the repository.

The repository contains the tests for 1.9.0 (`tests/test_issues_1_9_0.py`, `tests/conftest.py`, `tests/test_card_editor_title.js`); they run against synthetic data, not real hardware. The 1.8.0 tests for `dns_settings.py` and `static_ip.py` are not checked in.

## Version history

### 2.0.0b5 – Online Monitor: alternative interface paths

**Beta (pre-release).** Builds on 2.0.0b4. **Not tested on a real FRITZ!Box.**

- **Fixed (attempt):** a real box answered `api/v0/monitor/datasets` with “bad path”. The integration now tries `api/v0/monitor/…` and `api/v0/generic/monitor/…` in turn, remembers the working one and lists all error messages on failure. Diagnostics and the status sensor show `schnittstelle` (interface) and the FRITZ!OS version. Whether either variant exists on your box is unverified.

### 2.0.0b4 – Online Monitor request: headers and error text

**Beta (pre-release).** Builds on 2.0.0b3. **Not tested on a real FRITZ!Box.**

- **Fixed (attempt):** the request `api/v0/monitor/datasets` failed with HTTP 400 on a real box. It now sends the same headers as the community script the interface is based on (`Content-Type`, `Accept`, `Referer`). Whether that was the cause is unverified.
- **Better:** on an HTTP error the start of the box's response appears in the status sensor and the log.

### 2.0.0b3 – Sensors for data usage, status sensor

**Beta (pre-release).** Builds on 2.0.0b2. **Not tested on a real FRITZ!Box or in a running Home Assistant.**

- **New:** sensors *Data usage status*, *Data usage 7 days (all devices)*, *Biggest data consumer (7 days)* and, per device, *Daten 7 Tage* and *Daten heute* (only with the option on).
- **Better:** the status sensor names the reason when no values appear. If no counter at all was mapped to a device, the next poll (2 minutes) retries instead of waiting 15.

### 2.0.0b2 – Data usage per device (7 days, experimental)

**Beta (pre-release).** Builds on 2.0.0b1. **Not tested on a real FRITZ!Box or in a running Home Assistant** – only against a simulated box.

- **New (#26, partly):** options “Record data usage per device” and “Unit of the online monitor values”. The integration reads the Online Monitor's per-device data rates, integrates them into daily/7-day totals (download, upload, today) and stores them permanently. Prerequisite: “Save internet data rates” per device in the box. Values are estimates; unit, window length and mapping are unverified. Diagnostics: `traffic`.
- **New (card):** column “Data (7 days)” (sortable, only visible with data, `show_traffic`), popup rows with daily trend, CSV export in bytes.

### 2.0.0b1 – Static IP via REST, reservations and VPN devices, README in five languages

**Beta (pre-release).** Builds on 1.9.2b1. **None of it was tested on a real FRITZ!Box or in a running Home Assistant** – only against a simulated box and synthetic data.

- **Fixed (changing the IP address):** `set_static_ip` and the “Static IP” row in the card did not work. Cause: the form fields of `data.lua` were only assumed and the box never accepted them. The integration now writes through the REST route that a third-party project documents for FRITZ!OS 8.25 (`PUT /api/v0/generic/landevice/landevice/<UID>`), reads the result back (`query.lua`, otherwise REST or `edit_device`), reports a missing or silently discarded change as an error (with a hint on the two-factor confirmation) and restores a previous assignment. The old path remains as a fallback. The `ip` field of the request is untested even in the third-party project.
- **Fixed (#30):** `set_dns_settings` still rolled back the IPv4 value on a FRITZ!Box 6591 Cable after 1.9.1. Cause: the value read back was compared as a raw string, and the box shortens a single zero group of an IPv6 address to `::` while the integration kept `:0:`. IP addresses are now compared as addresses, both in the check after an HTTP error and in the final check. Reproduced and fixed against a simulated box.
- **Fixed (#31):** devices with “Assign permanent IPv4 address” inside the DHCP range showed as “dynamic” and were missing from the “Fixed IP” filter (the box does not report this via TR-064). The integration now also reads the reservations from the web interface (`query.lua`, otherwise `netDev`, in the cycle of the IP type collection) and counts them as fixed. **Untested on a box:** the field names are taken from third-party descriptions; if the box does not deliver the flag, nothing changes. The diagnostics download shows under `reservations` which way worked.
- **Fixed (#29, probable cause):** entries without a MAC address were dropped as stale – WireGuard peers have none. Peers marked as VPN that have an IP address are now kept with the identifier `VPN:<IP>` and shown as active; they get no entities and no MAC-dependent actions. **Whether the box reports WireGuard peers in its host list is untested**; `box_hosts.without_mac_samples` in the diagnostics shows how it marks them.
- **Fixed (#24, one possible cause):** the setting “Hide disconnected devices” also emptied the “Inactive” and “Long offline” views. These views now show offline devices; the setting only applies to the mixed views (help text added). Not every reporter's cause is confirmed.
- **New:** filter button **VPN** in the filter bar of the card (next to “Fixed IP”): shows devices the box flags as VPN and entries kept as `VPN:<IP>`. Hide with `filter_vpn: false`, `default_filter: vpn` possible, icon colour `color_cat_vpn`. Only checked with a syntax check of the card, not in a browser.
- **Documentation:** the README is now available in **five languages** (de, en, nl, fr, es) with a language bar at the top of each file. The integration and the card are still translated into de, en and nl.
- **Not solved:** #26 (data volume per device) – TR-064 provides none, the issue stays open. #20 was solved in 1.9.1 and confirmed by the reporter; #28 is a HACS matter.

### 1.9.2b1 – Notification Center (optional), update notice for pre-releases

**Beta (pre-release).** Builds on 1.9.1. **None of it was tested against a real Notification Center, on a real FRITZ!Box or in a running Home Assistant** – the bridge and triggers only run against a simulated event bus.

- **New:** optional connection to the **Notification Center** (interface schema 1, event bus, no MQTT). Message types: *Connection to FRITZ!Box lost* (warning), *Monitored device offline* (info; repeaters and devices selected by IP pattern) and *New device on the network* (info). Texts in five languages; only the initial state without push at startup. Without the Notification Center nothing changes. See [Notification Center](#notification-center-optional).
- **New:** two settings under *Configure*: master switch and selection of the message types to send (translations de/en/nl). The diagnostics download lists the switch state and a counter per message type, no contents.
- **Improved:** with a beta or release candidate installed, the update check also considers pre-releases (release list instead of `releases/latest`, which never returns pre-releases). With a final version installed you still only see final versions.
- **Note:** HACS only shows pre-releases with “Show beta versions” enabled.
- **Not implemented:** a “Notification Center” section in the dashboard card (cog). The card has no settings page and no interface for writing yet; the switches are in the Configure dialog.

### 1.9.1 – Selectable guest Wi-Fi service, IPv6 DNS with HTTP 400, extended diagnostics

Builds on 1.9.0. **None of it was tested on a real FRITZ!Box or in a running Home Assistant** – only against synthetic data.

- **New (#20):** setting **“Guest Wi-Fi service”** (automatic, 1–4). The card passes the known service number to `gast_wlan_info` (attribute `controls.guest_service`); the guest switch and QR code follow the same number. The diagnostics download lists `wlan_service_bands`. The suggestion from the issue (fixed service 4) was not adopted because the guest network is service 3 on other boxes.
- **Fixed (#30):** `set_dns_settings` rolled back the IPv4 value on a FRITZ!Box 6591 Cable because writing `home_ipv6_dns` answers with HTTP 400 although the box applies the value. An HTTP error while writing IPv6 now counts as written if re-reading shows the wanted value (with a `hinweis` in the response); otherwise nothing changes. Untested on a box.
- **Fixed (#17):** the **card title** jumped back to “Netzwerkgeräte” in the editor when deleting the last character. Cause: current Home Assistant reports a cleared text field as `undefined` instead of an empty string, which was not recognised as “deliberately cleared”. An **empty title is now allowed**: it stays empty, is saved as an empty string and the card then shows no header. A new card without a title still shows “Netzwerkgeräte”. Tested in the browser against simulated Home Assistant behaviour, not in a real dashboard.
- **Improved (#24):** the diagnostics download and the debug log state how many devices the box delivered (`box_hosts`: `raw_total`, `raw_active`, `raw_without_mac`). **The cause of vanishing offline devices has not been found or fixed.**
- **Documentation:** troubleshooting for #28 (HACS shows updates only after “Update information”) and #24; note on VPN devices (#29) under known limitations.
- **Not implemented:** #29 (VPN peers in the device list) – cannot be verified without a box or sample data; #26 (data volume per device) – not available via TR-064; #28 is a HACS matter, not the integration's.

### 1.9.0 – Mesh detection, guest Wi-Fi service, bulk “reserved” marker, repeater login

Addresses the open GitHub issues as far as possible without a real box. **None of it was tested on a real FRITZ!Box or in a running Home Assistant** – only against synthetic data.

- **New (#27):** group the list by **mesh connection** (`group_by: mesh`).
- **Improved (load):** fewer requests to the FRITZ!Box. Rarely changing data (band per device, mesh topology, external IP, line sync rates) is fetched at most every 5 minutes instead of on every update (roughly 10–20 fewer TR-064 calls per cycle, depending on setup). The smallest polling interval is now 30 s (was 15 s); smaller stored values are raised to 30 s. The effect is calculated, not measured on a box or in Home Assistant.
- **Improved (card):** the list is redrawn at most every `refresh_interval` seconds (default 15, `0` = immediately as before), waits while you scroll or interact and keeps the scroll position – the card no longer jumps to the top. Small fluctuations of the link rate no longer trigger a redraw. Untested in a browser (only a Node test of the throttle).
- **Fixed (#21):** the **Wi-Fi band** was missing for devices behind a repeater; it is now also read from the mesh topology (interface name such as `AP:5G:0` – assumption untested). A band from the box's own Wi-Fi list takes precedence.
- **Fixed (#16):** **not all mesh repeaters were detected**: besides the model name, every mesh member per the topology (`is_meshed`) now counts (untested).
- **Fixed (#20):** the **guest Wi-Fi QR code** showed a main network on boxes with more than three Wi-Fi services. The guest service is now detected (highest service from 3 up that reports no band, otherwise 3 as before); the guest switch follows the same choice; `gast_wlan_info` accepts an optional `service` and returns `dienst`. The assumption "guest reports no band" is untested.
- **Fixed (#25):** **repeater restart** failed for repeaters with a password only: after a rejected login it retries with an empty user name.
- **New (#22, #23):** service `mark_devices_reserved` marks many devices as “reserved” by IP pattern (Home Assistant only). The box does not report reservations *inside* the DHCP range via TR-064, so such devices show as “dynamic” - an interface limit, not a bug.
- **Not fixed (#24):** *offline devices disappear* - no cause found in the code; the diagnostics download now includes active/inactive counts.
- **Not implemented (#26):** *data volume per device* - TR-064 provides no per-device traffic.
- **Already fixed, issue still open (#17):** the title no longer jumps back when deleting the last character (fixed in 1.6.3); new test `tests/test_card_editor_title.js`.

### 1.8.0 – DNS settings and static IP address (experimental)

- **New:** services `get_dns_settings` and `set_dns_settings` (option “Change DNS settings of the box (experimental)”, preview with `dry_run`).
- **New:** service `set_static_ip` and a “Static IP” row in the card popup (option “Set static IP address (experimental)”): fixed IPv4 address with a check against duplicate addresses and a restart notice. Category switch `show_static_ip`.
- **Basis:** web interface (REST `/api/v0/generic/…` for DNS, `data.lua` for static IP), not TR-064. **Writing is not tested on any real box; the static-IP field names are assumed.**
- Translations (de/en/nl) and tests against simulated boxes (47 cases).

Older versions: see the German [README.md](README.md#versionshistorie).

## License

MIT
