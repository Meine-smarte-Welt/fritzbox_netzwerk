"""Einrichtungsdialog fuer fritzbox_netzwerk."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from fritzconnection import FritzConnection
from fritzconnection.core.exceptions import (
    FritzAuthorizationError,
    FritzConnectionException,
    FritzSecurityError,
    FritzServiceError,
)
from requests.exceptions import ConnectionError as RequestsConnectionError

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback

from .const import (
    CONF_ADDRESS_SOURCE_INTERVAL,
    CONF_SCAN_INTERVAL,
    CONF_TRACK_ADDRESS_SOURCE,
    CONF_USE_TLS,
    DEFAULT_ADDRESS_SOURCE_INTERVAL,
    DEFAULT_HOST,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TRACK_ADDRESS_SOURCE,
    DEFAULT_USE_TLS,
    DEFAULT_USERNAME,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

DATA_SCHEMA_USER = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_USE_TLS, default=DEFAULT_USE_TLS): bool,
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
        self._serial_number: str = ""
        self._model: str = "FRITZ!Box"

    def _try_connect(self) -> str:
        """Prueft Erreichbarkeit, Anmeldung und Rechte (blockierend)."""
        try:
            connection = FritzConnection(
                address=self._host,
                user=self._username,
                password=self._password,
                use_tls=self._use_tls,
            )
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

        self._serial_number = str(
            connection.call_action("DeviceInfo1", "GetInfo").get("NewSerialNumber", "")
        )
        self._model = connection.modelname or "FRITZ!Box"
        return RESULT_SUCCESS

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Erster und einziger Einrichtungsschritt."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA_USER)

        self._host = user_input[CONF_HOST]
        self._username = user_input[CONF_USERNAME]
        self._password = user_input[CONF_PASSWORD]
        self._use_tls = user_input.get(CONF_USE_TLS, DEFAULT_USE_TLS)

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
            },
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Startet die erneute Anmeldung."""
        self._host = entry_data[CONF_HOST]
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
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
