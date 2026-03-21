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
    try:
        # Safely access nested dictionaries with null checks
        course = lesson.get("course") or {}
        meta_course = course.get("meta") if isinstance(course, dict) else {}
        meta_lesson = lesson.get("meta") or {}

        # Safely process teachers array
        teachers = lesson.get("teachers") or []
        teacher_names = []
        if isinstance(teachers, list):
            for t in teachers:
                if isinstance(t, dict):
                    teacher_names.append(t.get("shortcut", t.get("name", "")))

        # Safely process bookables array
        bookables = lesson.get("bookables") or []
        rooms = []
        if isinstance(bookables, list):
            for b in bookables:
                if isinstance(b, dict):
                    rooms.append(b.get("name", b.get("shortcut", "")))

        # Safely process grades array
        grades = lesson.get("grades") or []
        grade_names = []
        if isinstance(grades, list):
            for g in grades:
                if isinstance(g, dict):
                    grade_names.append(g.get("name", ""))

        kind = lesson.get("kind")  # None, "SUBSTITUTION", "CANCLED"
        
        # Safely process referenced lessons with recursion protection
        referenced = lesson.get("referenced_target_lessons") or []
        referenced_lessons = []
        if isinstance(referenced, list):
            for r in referenced:
                if isinstance(r, dict):
                    try:
                        referenced_lessons.append(_parse_lesson(r))
                    except Exception as ref_exc:  # noqa: BLE001
                        _LOGGER.warning("Failed to parse referenced lesson: %s", ref_exc)

        return {
            "id": lesson.get("id"),
            "begins_at": lesson.get("begins_at"),
            "ends_at": lesson.get("ends_at"),
            "subject": (meta_lesson.get("displayname") if isinstance(meta_lesson, dict) else None) or 
                      (meta_course.get("displayname") if isinstance(meta_course, dict) else "") or "",
            "shortname": (meta_lesson.get("shortname") if isinstance(meta_lesson, dict) else None) or 
                        (meta_course.get("shortname") if isinstance(meta_course, dict) else "") or "",
            "teachers": teacher_names,
            "rooms": rooms,
            "grades": grade_names,
            "hour": meta_lesson.get("displayname_hour", "") if isinstance(meta_lesson, dict) else "",
            "kind": kind,
            "comment": lesson.get("comment", ""),
            "displayname_kind": meta_lesson.get("displayname_kind", "") if isinstance(meta_lesson, dict) else "",
            "referenced_lessons": referenced_lessons,
        }
    except Exception as exc:  # noqa: BLE001
        _LOGGER.error("Failed to parse lesson %s: %s", lesson.get("id"), exc, exc_info=True)
        _LOGGER.debug("Problematic lesson data: %s", lesson)
        # Return a minimal valid lesson structure to prevent total failure
        return {
            "id": lesson.get("id"),
            "begins_at": lesson.get("begins_at"),
            "ends_at": lesson.get("ends_at"),
            "subject": "Unknown",
            "shortname": "",
            "teachers": [],
            "rooms": [],
            "grades": [],
            "hour": "",
            "kind": lesson.get("kind"),
            "comment": lesson.get("comment", ""),
            "displayname_kind": "",
            "referenced_lessons": [],
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
