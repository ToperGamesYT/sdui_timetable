"""Calendar platform for Sdui."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
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
    """Set up Sdui calendar from config entry."""
    coordinator: SduiCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SduiCalendar(coordinator, entry)])


def _lesson_to_event(lesson: dict) -> CalendarEvent | None:
    """Convert a lesson dict to a CalendarEvent."""
    begins_ts = lesson.get("begins_at")
    ends_ts = lesson.get("ends_at")
    if begins_ts is None or ends_ts is None:
        return None

    start = datetime.fromtimestamp(begins_ts, tz=timezone.utc)
    end = datetime.fromtimestamp(ends_ts, tz=timezone.utc)

    subject = lesson.get("subject", "Unknown")
    kind = lesson.get("kind")
    kind_label = lesson.get("displayname_kind", "")

    # Build summary
    if kind == "CANCLED":
        summary = f"[CANCELLED] {subject}"
    elif kind == "SUBSTITUTION":
        label = kind_label or "Substitution"
        summary = f"[{label.upper()}] {subject}"
    else:
        summary = subject

    teachers = ", ".join(lesson.get("teachers", []))
    rooms = ", ".join(lesson.get("rooms", []))
    comment = lesson.get("comment", "")
    hour = lesson.get("hour", "")

    desc_parts = []
    if hour:
        desc_parts.append(f"Hour: {hour}")
    if teachers:
        desc_parts.append(f"Teacher: {teachers}")
    if rooms:
        desc_parts.append(f"Room: {rooms}")
    if comment:
        desc_parts.append(f"Note: {comment}")

    return CalendarEvent(
        start=start,
        end=end,
        summary=summary,
        description="\n".join(desc_parts) if desc_parts else None,
        location=rooms or None,
    )


class SduiCalendar(CoordinatorEntity, CalendarEntity):
    """Calendar entity showing the full Sdui timetable."""

    _attr_icon = "mdi:school"

    def __init__(self, coordinator: SduiCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._attr_name = "Sdui Timetable"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming calendar event."""
        lesson = self.coordinator.next_lesson()
        if lesson is None:
            return None
        return _lesson_to_event(lesson)

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return events within a time range."""
        start_ts = start_date.timestamp()
        end_ts = end_date.timestamp()

        events: list[CalendarEvent] = []
        if not self.coordinator.data:
            return events

        for lesson in self.coordinator.data.get("all_lessons", []):
            begins = lesson.get("begins_at", 0)
            ends = lesson.get("ends_at", 0)
            if ends < start_ts or begins > end_ts:
                continue
            evt = _lesson_to_event(lesson)
            if evt is not None:
                events.append(evt)

        return events
