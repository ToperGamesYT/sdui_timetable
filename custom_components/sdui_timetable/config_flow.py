"""Config flow for Sdui integration."""
from __future__ import annotations

import logging

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SduiApiClient, SduiApiError, SduiAuthError
from .const import CONF_TOKEN, CONF_USER_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SduiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sdui."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            session = async_get_clientsession(self.hass)
            client = SduiApiClient(token, session)

            try:
                user_id = await client.validate_token()
            except SduiAuthError:
                errors["base"] = "invalid_auth"
            except SduiApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during Sdui config flow")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Sdui (user {user_id})",
                    data={CONF_TOKEN: token, CONF_USER_ID: user_id},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return SduiOptionsFlow(config_entry)


class SduiOptionsFlow(config_entries.OptionsFlow):
    """Handle options (token renewal)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options — allow updating the Bearer token."""
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            session = async_get_clientsession(self.hass)
            client = SduiApiClient(token, session)

            try:
                await client.validate_token()
            except SduiAuthError:
                errors["base"] = "invalid_auth"
            except SduiApiError:
                errors["base"] = "cannot_connect"
            else:
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data={**self._config_entry.data, CONF_TOKEN: token},
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TOKEN,
                        default=self._config_entry.data.get(CONF_TOKEN, ""),
                    ): str
                }
            ),
            errors=errors,
        )
