"""
tr4ker.net scraper.

Uses the official API endpoint /api/me with an API key sent as the
X-Api-Key header. Generate the key from Mon Compte → Profil → Clé API.

The API returns raw and bonus traffic separately. We sum them to match
the totals displayed on the site (same convention as torr9.py).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import MissingCredentialsError, ScrapingError
from app.scrapers.common import DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)

API_URL = "https://tr4ker.net/api/me"


def is_enabled(settings: Settings) -> bool:
    return bool(settings.tr4ker_token or settings.tr4ker_api_key)


async def get_stats(headless: bool = True) -> dict[str, Any]:
    del headless

    settings = get_settings()
    api_key = settings.tr4ker_token or settings.tr4ker_api_key
    if not api_key:
        raise MissingCredentialsError(
            "Missing TR4KER_TOKEN/TR4KER_API_KEY — generate one at "
            "tr4ker.net → Mon Compte → Profil → Clé API and set it in .env."
        )

    headers = {
        "X-Api-Key": api_key,
        "Accept": "application/json",
        "User-Agent": DEFAULT_USER_AGENT,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            resp = await client.get(API_URL)
    except httpx.HTTPError as e:
        raise ScrapingError(f"Failed to reach tr4ker API: {e}") from e

    if resp.status_code == 401:
        raise ScrapingError("tr4ker: 401 Unauthorized — API key invalid or expired.")
    if resp.status_code >= 400:
        raise ScrapingError(
            f"tr4ker: HTTP {resp.status_code} from {API_URL}: {resp.text[:300]}"
        )

    try:
        data = resp.json()
    except ValueError as e:
        raise ScrapingError(f"tr4ker: response was not JSON: {e}") from e

    # Raw + bonus traffic, matching the totals displayed on the site.
    raw_upload = float(data.get("uploaded", 0)) + float(data.get("bonus_upload", 0))
    raw_download = float(data.get("downloaded", 0)) + float(data.get("bonus_download", 0))
    bonus = float(data.get("money", 0))

    return {
        "raw_upload": raw_upload,
        "raw_download": raw_download,
        "bonus": bonus,
    }
