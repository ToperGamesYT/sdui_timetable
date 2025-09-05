import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

class SDUITimetableConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SDUI Timetable."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Здесь можно проверить токен
            return self.async_create_entry(title="SDUI Timetable", data=user_input)

        schema = vol.Schema({
            vol.Required("token"): str,
            vol.Required("user_id"): str,
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
