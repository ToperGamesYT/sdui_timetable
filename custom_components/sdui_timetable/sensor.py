"""SDUI Timetable sensors."""
from __future__ import annotations

import datetime
import logging
from typing import Any

import aiohttp
import async_timeout

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import STATE_UNAVAILABLE

_LOGGER = logging.getLogger(__name__)

API_URL = "https://api.sdui.app/v1/timetables/users/{}/timetable?begins_at={}&ends_at={}"

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the SduiTimetable sensor from a config entry."""
    user_id = entry.data["user_id"]
    token = entry.data["token"]
    name = entry.title

    async_add_entities([SduiTimetableSensor(name, user_id, token)], True)


class SduiTimetableSensor(SensorEntity):
    """Representation of an Sdui Timetable sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, name: str, user_id: str, token: str) -> None:
        """Initialize the sensor."""
        self._attr_name = name
        self._user_id = user_id
        self._token = token
        self._attr_state = None
        self._attr_extra_state_attributes = {}
        # The unique ID is crucial for Home Assistant to identify the entity
        # This allows for UI configuration and consistent entity behavior
        self._attr_unique_id = f"sdui_timetable_{user_id}"

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        today = datetime.date.today().strftime("%Y-%m-%d")
        url = API_URL.format(self._user_id, today, today)
        headers = {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}
        session = async_get_clientsession(self.hass)

        try:
            async with async_timeout.timeout(15):
                async with session.get(url, headers=headers) as resp:
                    resp.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                    data = await resp.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching data from SDUI API: %s", err)
            self._attr_state = STATE_UNAVAILABLE
            return
        except TimeoutError:
            _LOGGER.error("Timeout fetching data from SDUI API")
            self._attr_state = STATE_UNAVAILABLE
            return
        except Exception as err:
            _LOGGER.error("Unexpected error occurred: %s", err)
            self._attr_state = STATE_UNAVAILABLE
            return

        lessons = data.get("data", {}).get("lessons", [])
        active_lessons = [lesson for lesson in lessons if lesson.get("kind") != "CANCELED"]

        if not active_lessons:
            self._attr_state = "No lessons today"
            self._attr_extra_state_attributes = {"lessons": []}
            return

        self._attr_state = f"{len(active_lessons)} lessons today"
        
        # Sort lessons by start time
        sorted_lessons = sorted(active_lessons, key=lambda l: l.get("begins_at", 0))
        first_lesson = sorted_lessons[0]

        lesson_list = [
            {
                "time": datetime.datetime.fromtimestamp(l.get("begins_at", 0)).strftime("%H:%M"),
                "subject": l.get("course", {}).get("meta", {}).get("displayname", "Unknown"),
                "status": l.get("meta", {}).get("displayname_kind", "Planned"),
            }
            for l in sorted_lessons
        ]

        self._attr_extra_state_attributes = {
            "first_lesson_time": datetime.datetime.fromtimestamp(first_lesson.get("begins_at", 0)).strftime("%H:%M"),
            "first_lesson_subject": first_lesson.get("course", {}).get("meta", {}).get("displayname", "Unknown"),
            "first_lesson_status": first_lesson.get("meta", {}).get("displayname_kind", "Planned"),
            "lessons": lesson_list,
        }
