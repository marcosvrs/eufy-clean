from __future__ import annotations

import logging
import random
import string
from typing import Any

import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from voluptuous import All, Optional, Range, Required, Schema

from .api.http import EufyAuthError, EufyConnectionError, EufyHTTPClient
from .const import DOMAIN, VACS

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = Schema(
    {
        Required(CONF_USERNAME): cv.string,
        Required(CONF_PASSWORD): cv.string,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eufy Robovac."""

    VERSION = 1
    data: dict[str, Any] | None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> EufyCleanOptionsFlowHandler:
        return EufyCleanOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=USER_SCHEMA)
        errors = {}
        username = user_input[CONF_USERNAME]
        await self.async_set_unique_id(username)
        self._abort_if_unique_id_configured()

        errors = await self._validate_login(username, user_input[CONF_PASSWORD])

        if not errors:
            data = user_input.copy()
            data[VACS] = {}
            return self.async_create_entry(title=username, data=data)

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry
        current_username = entry.data[CONF_USERNAME]

        if user_input is None:
            schema = Schema(
                {
                    Required(CONF_USERNAME, default=current_username): cv.string,
                    Required(CONF_PASSWORD): cv.string,
                }
            )
            return self.async_show_form(
                step_id="reconfigure", data_schema=schema, description_placeholders={}
            )

        errors = {}
        username = user_input[CONF_USERNAME]

        # Verify username matches existing entry (optional, but robust)
        if username != current_username:
            errors[CONF_USERNAME] = "username_mismatch"
        else:
            errors = await self._validate_login(username, user_input[CONF_PASSWORD])

        if not errors:
            return self.async_update_reload_and_abort(
                entry,
                data={**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]},
            )

        schema = Schema(
            {
                Required(CONF_USERNAME, default=current_username): cv.string,
                Required(CONF_PASSWORD): cv.string,
            }
        )
        return self.async_show_form(
            step_id="reconfigure", data_schema=schema, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth confirmation."""
        reauth_entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = await self._validate_login(
                reauth_entry.data[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            if not errors:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data={
                        **reauth_entry.data,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

        schema = Schema({Required(CONF_PASSWORD): cv.string})
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={"name": reauth_entry.data[CONF_USERNAME]},
        )

    async def _validate_login(self, username: str, password: str) -> dict[str, str]:
        """Validate login credentials."""
        errors: dict[str, str] = {}
        try:
            openudid = "".join(random.choices(string.hexdigits, k=32))
            _LOGGER.info("Trying to login with username: %s", username)

            session = async_get_clientsession(self.hass)
            eufy_api = EufyHTTPClient(username, password, openudid, session=session)
            login_resp = await eufy_api.login(validate_only=True)
            if not login_resp.get("session"):
                errors["base"] = "invalid_auth"
        except EufyAuthError:
            _LOGGER.warning("Authentication failed for %s", username)
            errors["base"] = "invalid_auth"
        except EufyConnectionError:
            _LOGGER.warning("Connection to Eufy servers failed for %s", username)
            errors["base"] = "cannot_connect"
        except Exception as e:
            _LOGGER.exception("Unexpected exception: %s", e)
            errors["base"] = "unknown"

        return errors


class EufyCleanOptionsFlowHandler(OptionsFlow):

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get("max_cleaning_history", 100)
        schema = Schema(
            {
                Optional("max_cleaning_history", default=current): All(
                    int, Range(min=10, max=500)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
