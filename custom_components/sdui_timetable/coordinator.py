"""DataUpdateCoordinator for Sdui."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SduiApiClient, SduiApiError, SduiAuthError
from .const import DOMAIN, SCAN_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)


def _parse_lesson(lesson: dict) -> dict:
    """Normalize a raw API lesson into a flat dict."""
    course = lesson.get("course", {})
    meta_course = course.get("meta", {})
    meta_lesson = lesson.get("meta", {})

    teachers = lesson.get("teachers", [])
    teacher_names = [t.get("shortcut", t.get("name", "")) for t in teachers]

    bookables = lesson.get("bookables", [])
    rooms = [b.get("name", b.get("shortcut", "")) for b in bookables]

    grades = lesson.get("grades", [])
    grade_names = [g.get("name", "") for g in grades]

    kind = lesson.get("kind")  # None, "SUBSTITUTION", "CANCLED"
    referenced = lesson.get("referenced_target_lessons", [])

    return {
        "id": lesson.get("id"),
        "begins_at": lesson.get("begins_at"),
        "ends_at": lesson.get("ends_at"),
        "subject": meta_lesson.get("displayname") or meta_course.get("displayname", ""),
        "shortname": meta_lesson.get("shortname") or meta_course.get("shortname", ""),
        "teachers": teacher_names,
        "rooms": rooms,
        "grades": grade_names,
        "hour": meta_lesson.get("displayname_hour", ""),
        "kind": kind,
        "comment": lesson.get("comment", ""),
        "displayname_kind": meta_lesson.get("displayname_kind", ""),
        "referenced_lessons": [_parse_lesson(r) for r in referenced],
    }


class SduiCoordinator(DataUpdateCoordinator):
    """Fetches and organizes Sdui timetable data."""

    def __init__(self, hass: HomeAssistant, client: SduiApiClient) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=SCAN_INTERVAL_MINUTES),
        )
        self._client = client

    async def _async_update_data(self) -> dict:
        """Fetch timetable for the next 14 days."""
        today = datetime.now().date()
        end = today + timedelta(days=14)

        try:
            lessons_raw = await self._client.fetch_timetable(
                today.strftime("%Y-%m-%d"),
                end.strftime("%Y-%m-%d"),
            )
        except SduiAuthError as exc:
            raise UpdateFailed(f"Authentication error: {exc}") from exc
        except SduiApiError as exc:
            raise UpdateFailed(f"API error: {exc}") from exc

        lessons = [_parse_lesson(l) for l in lessons_raw]

        # Group by date (local date of begins_at unix timestamp)
        by_date: dict[str, list[dict]] = {}
        for lesson in lessons:
            ts = lesson.get("begins_at")
            if ts is None:
                continue
            date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            by_date.setdefault(date_str, []).append(lesson)

        # Sort each day's lessons by start time
        for date_str in by_date:
            by_date[date_str].sort(key=lambda x: x.get("begins_at", 0))

        today_str = today.strftime("%Y-%m-%d")

        return {
            "lessons_by_date": by_date,
            "today": today_str,
            "all_lessons": lessons,
        }

    def today_lessons(self) -> list[dict]:
        """Return today's lessons."""
        if not self.data:
            return []
        today = self.data["today"]
        return self.data["lessons_by_date"].get(today, [])

    def next_lesson(self) -> dict | None:
        """Return the next upcoming lesson (from now on)."""
        if not self.data:
            return None
        now_ts = datetime.now().timestamp()
        for lesson in self.data["all_lessons"]:
            begins = lesson.get("begins_at", 0)
            ends = lesson.get("ends_at", 0)
            # Accept currently-running or upcoming lessons
            if ends and ends >= now_ts:
                return lesson
        return None

    def substitutions_today(self) -> list[dict]:
        """Return today's substitutions and cancellations."""
        return [
            l for l in self.today_lessons()
            if l.get("kind") in ("SUBSTITUTION", "CANCLED")
        ]
