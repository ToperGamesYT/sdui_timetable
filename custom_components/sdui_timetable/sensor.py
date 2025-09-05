"""SDUI Timetable sensors."""
from __future__ import annotations
import aiohttp
import async_timeout
import datetime
import voluptuous as vol
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import HomeAssistantType, ConfigType

CONF_USER_ID = "user_id"
CONF_TOKEN = "token"

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USER_ID): cv.string,
    vol.Required(CONF_TOKEN): cv.string,
    vol.Optional(CONF_NAME, default="SDUI Timetable"): cv.string,
})

API_URL = "https://api.sdui.app/v1/timetables/users/{}/timetable?begins_at={}&ends_at={}"

async def async_setup_platform(hass: HomeAssistantType, config: ConfigType, async_add_entities: AddEntitiesCallback, discovery_info=None):
    user_id = config[CONF_USER_ID]
    token = config[CONF_TOKEN]
    name = config[CONF_NAME]
    async_add_entities([SduiTimetableSensor(name, user_id, token)], True)

class SduiTimetableSensor(SensorEntity):
    def __init__(self, name, user_id, token):
        self._attr_name = name
        self._user_id = user_id
        self._token = token
        self._attr_state = None
        self._attr_extra_state_attributes = {}

    async def async_update(self):
        today = datetime.date.today().strftime("%Y-%m-%d")
        url = API_URL.format(self._user_id, today, today)
        headers = {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}
        session = async_get_clientsession(self.hass)

        try:
            with async_timeout.timeout(15):
                async with session.get(url, headers=headers) as resp:
                    data = await resp.json()
        except Exception as e:
            self._attr_state = f"Error: {e}"
            return

        lessons = data.get("data", {}).get("lessons", [])
        active_lessons = [l for l in lessons if l.get("kind") != "CANCLED"]

        self._attr_state = f"{len(active_lessons)} уроков" if active_lessons else "Нет уроков"
        if active_lessons:
            first = sorted(active_lessons, key=lambda l: l["begins_at"])[0]
            self._attr_extra_state_attributes = {
                "first_lesson_time": datetime.datetime.fromtimestamp(first["begins_at"]).strftime("%H:%M"),
                "first_lesson_subject": first["course"]["meta"]["displayname"],
                "first_lesson_status": first["meta"].get("displayname_kind") or "Планово",
                "lessons": [
                    {
                        "time": datetime.datetime.fromtimestamp(l["begins_at"]).strftime("%H:%M"),
                        "subject": l["course"]["meta"]["displayname"],
                        "status": l["meta"].get("displayname_kind") or "Планово"
                    }
                    for l in active_lessons
                ]
            }
