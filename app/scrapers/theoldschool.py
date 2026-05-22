from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import MissingCredentialsError, ScrapingError
from app.scrapers.common import DEFAULT_USER_AGENT, parse_bytes

USER_STATS_URL = "https://theoldschool.cc/api/user"


def is_enabled(settings: Settings) -> bool:
    return bool(settings.tos_token)


async def get_stats(headless: bool = True) -> dict[str, Any]:
    del headless

    from app.core.config import get_settings

    token = get_settings().tos_token
    if not token:
        raise MissingCredentialsError("Missing TOS_TOKEN")

    url = f"{USER_STATS_URL}?api_token={token}"
    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"},
        ) as client:
            response = await client.get(url)
    except httpx.HTTPError as exc:
        raise ScrapingError(f"Failed to reach TheOldSchool API: {exc}") from exc

    if response.status_code >= 400:
        raise ScrapingError(f"Failed to get TheOldSchool stats: HTTP {response.status_code}")

    api_data = response.json()
    return {
        "raw_upload": parse_bytes(str(api_data.get("uploaded", "0"))),
        "raw_download": parse_bytes(str(api_data.get("downloaded", "0"))),
        "bonus": float(api_data.get("seedbonus", 0)),
    }
