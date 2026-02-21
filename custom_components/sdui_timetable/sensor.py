"""Sensor platform for Sdui."""
from __future__ import annotations

from datetime import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SduiCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sdui sensors from config entry."""
    coordinator: SduiCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            SduiNextLessonSensor(coordinator, entry),
            SduiTodayLessonsSensor(coordinator, entry),
            SduiSubstitutionsSensor(coordinator, entry),
        ]
    )


def _format_time(ts: int | None) -> str | None:
    """Format a Unix timestamp to HH:MM local time."""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts).strftime("%H:%M")


def _lesson_to_attr(lesson: dict) -> dict:
    """Convert a lesson dict to a simplified attribute dict."""
    return {
        "subject": lesson.get("subject"),
        "shortname": lesson.get("shortname"),
        "teachers": lesson.get("teachers", []),
        "rooms": lesson.get("rooms", []),
        "grades": lesson.get("grades", []),
        "hour": lesson.get("hour"),
        "kind": lesson.get("kind"),
        "kind_label": lesson.get("displayname_kind"),
        "comment": lesson.get("comment"),
        "start": _format_time(lesson.get("begins_at")),
        "end": _format_time(lesson.get("ends_at")),
    }


class SduiNextLessonSensor(CoordinatorEntity, SensorEntity):
    """Sensor: next upcoming lesson."""

    _attr_icon = "mdi:school"

    def __init__(self, coordinator: SduiCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_next_lesson"
        self._attr_name = "Sdui Next Lesson"

    @property
    def native_value(self) -> str | None:
        """Return subject name of the next lesson."""
        lesson = self.coordinator.next_lesson()
        if lesson is None:
            return None
        return lesson.get("subject")

    @property
    def extra_state_attributes(self) -> dict:
        """Return detailed info about the next lesson."""
        lesson = self.coordinator.next_lesson()
        if lesson is None:
            return {}
        return _lesson_to_attr(lesson)


class SduiTodayLessonsSensor(CoordinatorEntity, SensorEntity):
    """Sensor: number of lessons today."""

    _attr_icon = "mdi:calendar-today"
    _attr_native_unit_of_measurement = "lessons"

    def __init__(self, coordinator: SduiCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_lessons_today"
        self._attr_name = "Sdui Lessons Today"

    @property
    def native_value(self) -> int:
        """Return count of today's lessons."""
        return len(self.coordinator.today_lessons())

    @property
    def extra_state_attributes(self) -> dict:
        """Return list of today's lessons."""
        return {
            "lessons": [_lesson_to_attr(l) for l in self.coordinator.today_lessons()]
        }


class SduiSubstitutionsSensor(CoordinatorEntity, SensorEntity):
    """Sensor: substitutions and cancellations today."""

    _attr_icon = "mdi:swap-horizontal"
    _attr_native_unit_of_measurement = "changes"

    def __init__(self, coordinator: SduiCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_substitutions_today"
        self._attr_name = "Sdui Substitutions Today"

    @property
    def native_value(self) -> int:
        """Return count of substitutions/cancellations today."""
        return len(self.coordinator.substitutions_today())

    @property
    def extra_state_attributes(self) -> dict:
        """Return details of today's substitutions."""
        return {
            "substitutions": [
                _lesson_to_attr(l) for l in self.coordinator.substitutions_today()
            ]
        }
