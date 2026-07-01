"""Sdui API client."""
from __future__ import annotations

import base64
import json
import logging
from datetime import datetime

import aiohttp

from .const import API_BASE

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    "Host": "api.sdui.app",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://sdui.app",
    "Sec-Fetch-Site": "same-site",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Frontend-Version": "2024.4.1@656f3725032525caf2fba2804424e968b5ba456b",
    "Released-At": "2025-09-30 17:04:17",
}


class SduiAuthError(Exception):
    """Raised on 401/403 responses."""


class SduiApiError(Exception):
    """Raised on other API errors."""


def extract_user_id_from_token(token: str) -> str:
    """Extract user_id (sub claim) from JWT Bearer token."""
    try:
        # JWT format: header.payload.signature
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Not a valid JWT")
        # Add padding if needed
        payload = parts[1]
        payload += "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        claims = json.loads(decoded)
        return str(claims["sub"])
    except Exception as exc:  # noqa: BLE001
        raise SduiAuthError(f"Cannot extract user_id from token: {exc}") from exc


class SduiApiClient:
    """Async API client for sdui.app."""

    def __init__(self, token: str, session: aiohttp.ClientSession, user_id: str | None = None) -> None:
        """Initialize the API client."""
        self._token = token
        self._session = session
        # Use provided user_id or fall back to extracting from token (for backward compatibility)
        self._user_id = user_id if user_id else extract_user_id_from_token(token)

    @property
    def user_id(self) -> str:
        """Return the user ID."""
        return self._user_id

    def _auth_headers(self) -> dict:
        """Return headers including Authorization."""
        return {**HEADERS, "Authorization": f"Bearer {self._token}"}

    async def fetch_timetable(
        self, begins_at: str, ends_at: str
    ) -> list[dict]:
        """Fetch timetable lessons between two dates (YYYY-MM-DD format)."""
        url = (
            f"{API_BASE}/timetables/users/{self._user_id}/timetable"
            f"?begins_at={begins_at}&ends_at={ends_at}"
        )
        _LOGGER.debug("Fetching timetable: %s", url)

        try:
            async with self._session.get(
                url, headers=self._auth_headers(), timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status in (401, 403):
                    raise SduiAuthError(
                        f"Authentication failed. Status: {resp.status}"
                    )
                if resp.status != 200:
                    text = await resp.text()
                    raise SduiApiError(
                        f"Unexpected response {resp.status}: {text[:200]}"
                    )
                data = await resp.json()
                return data.get("data", {}).get("lessons", [])
        except aiohttp.ClientError as exc:
            raise SduiApiError(f"Network error: {exc}") from exc

    async def validate_token(self) -> str:
        """Validate the token by fetching today's timetable. Returns user_id on success."""
        today = datetime.now().strftime("%Y-%m-%d")
        # May return empty lessons, that's fine — just check no auth error
        await self.fetch_timetable(today, today)
        return self._user_id
