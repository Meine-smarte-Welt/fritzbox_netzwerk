🇩🇪 [Deutsch](README.md) · 🇬🇧 English · [🇳🇱 Nederlands](README.nl.md)

# FRITZ!Box Netzwerk

A Home Assistant integration that puts every device in the FRITZ!Box home network on your dashboard as a sortable table – with IP address, MAC address, connection type and the matching Home Assistant device name.

![Version](https://img.shields.io/badge/Version-1.9.0-blue)
![HACS](https://img.shields.io/badge/HACS-Custom-orange)

> This is the English edition. The German [README.md](README.md) is the main file and has the full card reference, the troubleshooting chapter and the complete version history. Sections marked “German only” are not translated yet.

---

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Setup](#setup)
- [Settings](#settings)
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
- **Filter bar**: All, Active, Inactive, Guest, Blocked, Update, Fixed IP – every button can be hidden individually
- **Wi-Fi band** (2.4 / 5 GHz), **manufacturer from the MAC address** (bundled list, no internet access), **copy MAC with one click**
- **IP filter with wildcards** (`192.168.2.*`) to split a large network over several cards
- **Detail popup** per device with all fields, Wake-on-LAN, rename, label/note/“reserved” marker and a jump to the Home Assistant device
- **Last seen**, **internet access switch** (experimental), **IP type** (fixed or dynamic)
- **Connection sensors** (down/upload rate, line sync rates, external IP, online time, connection state) and **events** (“new device”, “external IP changed”)
- **Mesh group**: FRITZ!Box and repeaters as one unit, button “Restart all FRITZ! devices”
- **Wi-Fi MAC filter** on/off and temporary release (“pairing”)
- **Parental control** (experimental): switch access profiles per device, also temporarily
- **DNS settings** of the box (experimental, since 1.8.0): read and change
- **Static IP address** per device (experimental, since 1.8.0): assign with a check against duplicate addresses, button in the popup
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
| Check daily for a new version | on | Asks GitHub once a day for the latest version; no data about you or the box is sent |
| Control parental-control access profiles (experimental) | off | Enables the services and the profile selection in the popup |
| Change DNS settings of the box (experimental) | off | Allows `set_dns_settings` to write; reading and the preview always work |
| Set static IP address (experimental) | off | Allows `set_static_ip` and the card button to write; the preview (`dry_run`) always works |
| Read CPU and RAM of the box (experimental) | off | Three sensors from the box web interface |
| Create network devices as own devices | off | One HA device per selected device, selected by pattern |
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
- **Safety net:** if the expected fields are missing in the box response, nothing is written. After writing the box is read again; on a mismatch the previous state is restored. The current access profile is sent along.

**Test status (honest):** the duplicate check is covered by tests. The **field names of the web interface** (`edit_device`) are **assumed** and not verified on any box – neither read nor written. If the layout does not match, the service reports “nothing changed”; please open an issue with the request the box sends when saving (browser developer tools → Network).

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
default_filter: aktiv   # alle | aktiv | inaktiv | gast | gesperrt | update | fest
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
| `gast_wlan_info` | Guest Wi-Fi data (for the QR code); since 1.9.0 the guest service is detected and an optional `service` (1-4) can force it |
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

German, English and Dutch – in the config flow, entities, services and the card (language from Home Assistant, fallback English).

## Security

Write actions need administrator rights; inputs are validated in the backend; texts in the card are escaped. Options for experimental write features are **off by default**, and risky actions have preview modes (`dry_run`) where possible.

---

## Known limitations

- **“Remove all unused connections” is missing** – TR-064 has no action for it.
- **Static IP and DNS write access are experimental** and use the undocumented web interface of the box. Writing is not verified on any real box; the field names for the static IP are assumed. They may break with any FRITZ!OS update.
- **Mesh only in parts:** no signal strength in dBm.
- **Data volume per device** is not provided by the box via TR-064.
- Devices are matched to Home Assistant devices only by MAC address.
- The full list is in the German README.

## Troubleshooting

German only: see the chapter “Fehlerbehebung” in [README.md](README.md#fehlerbehebung). Logger: `custom_components.fritzbox_netzwerk`; the diagnostics download is anonymised.

## File integrity

Every `.py`, `.js` and `.yaml` file starts with a SHA-256 header over its content (from line 2). Check with `tail -n +2 file.py | sha256sum`. The hashes of the JSON files are listed in the German [README.md](README.md#datei-integrität).

## Development and tests

```bash
pip install fritzconnection==1.15.1 segno==1.6.6 pytest
python3 -m pytest -q tests
node tests/test_card_editor_title.js custom_components/fritzbox_netzwerk/www/fritzbox-netzwerk-card.js
```

The repository contains the tests for 1.9.0 (`tests/test_issues_1_9_0.py`, `tests/conftest.py`, `tests/test_card_editor_title.js`); they run against synthetic data, not real hardware. The 1.8.0 tests for `dns_settings.py` and `static_ip.py` are not checked in.

## Version history

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
