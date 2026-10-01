"""Einrichtungsdialog fuer fritzbox_netzwerk."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from fritzconnection.core.exceptions import (
    FritzAuthorizationError,
    FritzConnectionException,
    FritzSecurityError,
    FritzServiceError,
)
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .connection import create_connection
from .const import (
    CONF_ADDRESS_SOURCE_INTERVAL,
    CONF_ENABLE_CONTROLS,
    CONF_ENABLE_DEVICE_TRACKER,
    CONF_ENABLE_HOST_DEVICES,
    CONF_ENABLE_PARENTAL,
    CONF_ENABLE_SYSTEM_STATS,
    DEFAULT_ENABLE_PARENTAL,
    DEFAULT_ENABLE_SYSTEM_STATS,
    CONF_ENABLE_REPEATERS,
    CONF_HOST_DEVICE_FILTER,
    CONF_IP_RANGES,
    CONF_PAIRING_MINUTES,
    CONF_PORT,
    CONF_REMOTE_ACCESS,
    CONF_SCAN_INTERVAL,
    CONF_TRACK_ADDRESS_SOURCE,
    CONF_TRACK_WLAN_BAND,
    CONF_USE_TLS,
    DEFAULT_ADDRESS_SOURCE_INTERVAL,
    DEFAULT_ENABLE_CONTROLS,
    DEFAULT_ENABLE_DEVICE_TRACKER,
    DEFAULT_ENABLE_HOST_DEVICES,
    DEFAULT_ENABLE_REPEATERS,
    DEFAULT_HOST,
    DEFAULT_HOST_DEVICE_FILTER,
    DEFAULT_IP_RANGES,
    DEFAULT_PAIRING_MINUTES,
    DEFAULT_PORT,
    DEFAULT_REMOTE_ACCESS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TRACK_ADDRESS_SOURCE,
    DEFAULT_TRACK_WLAN_BAND,
    DEFAULT_USE_TLS,
    DEFAULT_USERNAME,
    DOMAIN,
    MAX_PAIRING_MINUTES,
    MAX_SCAN_INTERVAL,
    MIN_PAIRING_MINUTES,
    MIN_SCAN_INTERVAL,
)

DATA_SCHEMA_USER = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_USE_TLS, default=DEFAULT_USE_TLS): bool,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=65535)
        ),
        vol.Optional(CONF_REMOTE_ACCESS, default=DEFAULT_REMOTE_ACCESS): bool,
    }
)

RESULT_SUCCESS = "success"
RESULT_INVALID_AUTH = "invalid_auth"
RESULT_INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
RESULT_CANNOT_CONNECT = "cannot_connect"
RESULT_NO_HOSTS_SERVICE = "no_hosts_service"


class FritzboxNetzwerkConfigFlow(ConfigFlow, domain=DOMAIN):
    """Fuehrt durch die Einrichtung."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialisiert den Flow."""
        self._host: str = DEFAULT_HOST
        self._username: str = DEFAULT_USERNAME
        self._password: str = ""
        self._use_tls: bool = DEFAULT_USE_TLS
        self._port: int = 0
        self._remote_access: bool = False
        self._serial_number: str = ""
        self._model: str = "FRITZ!Box"

    def _try_connect(self) -> str:
        """Prueft Erreichbarkeit, Anmeldung und Rechte (blockierend)."""
        try:
            connection = create_connection({
                CONF_HOST: self._host,
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_USE_TLS: self._use_tls,
                CONF_PORT: self._port,
                CONF_REMOTE_ACCESS: self._remote_access,
            })
            # Der Hosts-Dienst ist die eigentliche Datenquelle. Wenn die
            # Rechte fehlen, faellt das genau hier auf - nicht erst
            # Stunden spaeter beim ersten Abruf.
            connection.call_action("Hosts1", "GetHostNumberOfEntries")
        except (FritzSecurityError, FritzAuthorizationError):
            return RESULT_INVALID_AUTH
        except FritzServiceError:
            return RESULT_NO_HOSTS_SERVICE
        except RequestsConnectionError:
            return RESULT_CANNOT_CONNECT
        except FritzConnectionException:
            return RESULT_INSUFFICIENT_PERMISSIONS

        # Die Seriennummer dient nur als interne Kennung (unique_id) und ist
        # fuer den Betrieb der Integration nicht erforderlich - die
        # eigentlichen Daten liefert der Hosts-Dienst, dessen Abfrage oben
        # schon erfolgreich war. Manche Modelle (beobachtet: FRITZ!Box 5690
        # Pro) lehnen DeviceInfo1/GetInfo trotz passender Zugangsdaten mit
        # HTTP 401 ab. Ohne dieses Abfangen fuehrte das zu einer
        # unbehandelten Ausnahme und der Einrichtungsdialog zeigte nur
        # "Unknown error" - obwohl Benutzername, Kennwort und Rechte in
        # Ordnung waren. Schlaegt die Abfrage fehl, wird stattdessen die
        # Host-Adresse als Kennung verwendet; die Einrichtung laeuft normal
        # weiter.
        try:
            self._serial_number = str(
                connection.call_action("DeviceInfo1", "GetInfo").get(
                    "NewSerialNumber", ""
                )
            )
        except (FritzConnectionException, RequestException):
            self._serial_number = ""
        self._model = connection.modelname or "FRITZ!Box"
        return RESULT_SUCCESS

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Erster und einziger Einrichtungsschritt."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA_USER)

        self._host = user_input[CONF_HOST].strip()
        self._port = user_input.get(CONF_PORT, DEFAULT_PORT)
        self._remote_access = user_input.get(CONF_REMOTE_ACCESS, DEFAULT_REMOTE_ACCESS)
        self._username = user_input[CONF_USERNAME]
        self._password = user_input[CONF_PASSWORD]
        self._use_tls = self._remote_access or user_input.get(CONF_USE_TLS, DEFAULT_USE_TLS)

        result = await self.hass.async_add_executor_job(self._try_connect)
        if result != RESULT_SUCCESS:
            return self.async_show_form(
                step_id="user",
                data_schema=DATA_SCHEMA_USER,
                errors={"base": result},
            )

        await self.async_set_unique_id(self._serial_number or self._host)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"{self._model} Netzwerk",
            data={
                CONF_HOST: self._host,
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_USE_TLS: self._use_tls,
                CONF_PORT: self._port,
                CONF_REMOTE_ACCESS: self._remote_access,
            },
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Startet die erneute Anmeldung."""
        self._host = entry_data[CONF_HOST]
        self._port = entry_data.get(CONF_PORT, DEFAULT_PORT)
        self._remote_access = entry_data.get(CONF_REMOTE_ACCESS, DEFAULT_REMOTE_ACCESS)
        self._username = entry_data[CONF_USERNAME]
        self._use_tls = entry_data.get(CONF_USE_TLS, DEFAULT_USE_TLS)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Fragt Benutzername und Passwort erneut ab."""
        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=self._username): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=schema,
                description_placeholders={"host": self._host},
            )

        self._username = user_input[CONF_USERNAME]
        self._password = user_input[CONF_PASSWORD]

        result = await self.hass.async_add_executor_job(self._try_connect)
        if result != RESULT_SUCCESS:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=schema,
                description_placeholders={"host": self._host},
                errors={"base": result},
            )

        return self.async_update_reload_and_abort(
            self._get_reauth_entry(),
            data_updates={
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
            },
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Aendert Adresse/Zugangsdaten/Fernzugriff, ohne die Integration neu anzulegen.

        Idee 16 aus feature-ideen.md: seit 1.6.3 gibt es mit Port und
        Fernzugriffsschalter (PR #19, 1.6.2) mehr Einstellungen, die Nutzer
        aendern moechten, ohne die Integration zu loeschen und neu
        einzurichten (und dabei z. B. den Reconfigure-Flow-Dialog ihrer
        Automationen/Dashboards neu verknuepfen zu muessen).

        Das Kennwort wird - wie beim bestehenden Reauth-Flow - immer neu
        abgefragt statt mit dem alten Wert vorausgefuellt, damit es nicht
        im Klartext in einem sichtbaren Formularfeld landet.
        """
        entry = self._get_reconfigure_entry()
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=entry.data[CONF_HOST]): str,
                vol.Required(CONF_USERNAME, default=entry.data[CONF_USERNAME]): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(
                    CONF_USE_TLS, default=entry.data.get(CONF_USE_TLS, DEFAULT_USE_TLS)
                ): bool,
                vol.Optional(
                    CONF_PORT, default=entry.data.get(CONF_PORT, DEFAULT_PORT)
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535)),
                vol.Optional(
                    CONF_REMOTE_ACCESS,
                    default=entry.data.get(CONF_REMOTE_ACCESS, DEFAULT_REMOTE_ACCESS),
                ): bool,
            }
        )

        if user_input is None:
            return self.async_show_form(step_id="reconfigure", data_schema=schema)

        self._host = user_input[CONF_HOST].strip()
        self._port = user_input.get(CONF_PORT, DEFAULT_PORT)
        self._remote_access = user_input.get(CONF_REMOTE_ACCESS, DEFAULT_REMOTE_ACCESS)
        self._username = user_input[CONF_USERNAME]
        self._password = user_input[CONF_PASSWORD]
        self._use_tls = self._remote_access or user_input.get(
            CONF_USE_TLS, DEFAULT_USE_TLS
        )

        result = await self.hass.async_add_executor_job(self._try_connect)
        if result != RESULT_SUCCESS:
            return self.async_show_form(
                step_id="reconfigure", data_schema=schema, errors={"base": result}
            )

        # Verhindert, dass eine geaenderte Adresse versehentlich auf eine
        # ANDERE, bereits vorhandene FRITZ!Box zeigt (erkennbar an einer
        # abweichenden Seriennummer). Wird die Seriennummer nicht geliefert
        # (siehe _try_connect - z. B. FRITZ!Box 5690 Pro), greift dieser
        # Schutz nicht, weil die bestehende Kennung dann ohnehin schon die
        # alte Host-Adresse war - ein bekanntes, bereits vor 1.6.3
        # bestehendes Verhalten der Kennungsvergabe.
        await self.async_set_unique_id(self._serial_number or self._host)
        self._abort_if_unique_id_mismatch()

        return self.async_update_reload_and_abort(
            entry,
            data_updates={
                CONF_HOST: self._host,
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_USE_TLS: self._use_tls,
                CONF_PORT: self._port,
                CONF_REMOTE_ACCESS: self._remote_access,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> FritzboxNetzwerkOptionsFlow:
        """Liefert den Options-Flow."""
        return FritzboxNetzwerkOptionsFlow()


class FritzboxNetzwerkOptionsFlow(OptionsFlowWithReload):
    """Einstellungen, die ohne Neuanlage geaendert werden koennen."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Zeigt und speichert die Optionen."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
                vol.Optional(
                    CONF_TRACK_ADDRESS_SOURCE,
                    default=options.get(
                        CONF_TRACK_ADDRESS_SOURCE, DEFAULT_TRACK_ADDRESS_SOURCE
                    ),
                ): bool,
                vol.Optional(
                    CONF_ADDRESS_SOURCE_INTERVAL,
                    default=options.get(
                        CONF_ADDRESS_SOURCE_INTERVAL, DEFAULT_ADDRESS_SOURCE_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440)),
                vol.Optional(
                    CONF_TRACK_WLAN_BAND,
                    default=options.get(CONF_TRACK_WLAN_BAND, DEFAULT_TRACK_WLAN_BAND),
                ): bool,
                vol.Optional(
                    CONF_ENABLE_DEVICE_TRACKER,
                    default=options.get(
                        CONF_ENABLE_DEVICE_TRACKER, DEFAULT_ENABLE_DEVICE_TRACKER
                    ),
                ): bool,
                vol.Optional(
                    CONF_ENABLE_REPEATERS,
                    default=options.get(
                        CONF_ENABLE_REPEATERS, DEFAULT_ENABLE_REPEATERS
                    ),
                ): bool,
                vol.Optional(
                    CONF_ENABLE_CONTROLS,
                    default=options.get(
                        CONF_ENABLE_CONTROLS, DEFAULT_ENABLE_CONTROLS
                    ),
                ): bool,
                vol.Optional(
                    CONF_PAIRING_MINUTES,
                    default=options.get(
                        CONF_PAIRING_MINUTES, DEFAULT_PAIRING_MINUTES
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_PAIRING_MINUTES, max=MAX_PAIRING_MINUTES),
                ),
                # Idee 7 aus feature-ideen.md: Zaehler-Sensoren je benanntem
                # IP-Bereich, z. B. "Drucker online: 2 von 3". Eine Zeile je
                # Bereich ("Name=Muster"), siehe hosts.parse_ip_ranges - dieselbe
                # Platzhalter-Syntax wie das Kartenfeld "IP-Filter".
                vol.Optional(
                    CONF_IP_RANGES,
                    default=options.get(CONF_IP_RANGES, DEFAULT_IP_RANGES),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
                # Idee 9 aus feature-ideen.md: Netzwerkgeraete als eigene
                # Home-Assistant-Geraete (mit Hersteller aus der OUI-Liste und
                # einem Verbunden-Status), nur fuer die ausgewaehlten Bereiche.
                vol.Optional(
                    CONF_ENABLE_HOST_DEVICES,
                    default=options.get(
                        CONF_ENABLE_HOST_DEVICES, DEFAULT_ENABLE_HOST_DEVICES
                    ),
                ): bool,
                vol.Optional(
                    CONF_ENABLE_SYSTEM_STATS,
                    default=options.get(
                        CONF_ENABLE_SYSTEM_STATS, DEFAULT_ENABLE_SYSTEM_STATS
                    ),
                ): bool,
                vol.Optional(
                    CONF_ENABLE_PARENTAL,
                    default=options.get(CONF_ENABLE_PARENTAL, DEFAULT_ENABLE_PARENTAL),
                ): bool,
                vol.Optional(
                    CONF_HOST_DEVICE_FILTER,
                    default=options.get(
                        CONF_HOST_DEVICE_FILTER, DEFAULT_HOST_DEVICE_FILTER
                    ),
                ): selector.TextSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
