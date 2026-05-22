"""
Nexum-Core scraper.

Uses the official API endpoint /api/v1/me with an API key sent as the
X-API-Key header. Generate the key from Paramètres → Clé API on the site
(this is different from your tracker passkey).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import MissingCredentialsError, ScrapingError
from app.scrapers.common import DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)

API_URL = "https://nexum-core.com/api/v1/me"


def is_enabled(settings: Settings) -> bool:
    return bool(settings.nexum_token)


async def get_stats(headless: bool = True) -> dict[str, Any]:
    del headless

    api_key = get_settings().nexum_token
    if not api_key:
        raise MissingCredentialsError(
            "Missing NEXUM_TOKEN — generate one at "
            "nexum-core.com → Paramètres → Clé API and set it in .env."
        )

    headers = {
        "X-API-Key": api_key,
        "Accept": "application/json",
        "User-Agent": DEFAULT_USER_AGENT,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            resp = await client.get(API_URL)
    except httpx.HTTPError as e:
        raise ScrapingError(f"Failed to reach nexum-core API: {e}") from e

    if resp.status_code == 401:
        raise ScrapingError("nexum-core: 401 Unauthorized — API key invalid or expired.")
    if resp.status_code >= 400:
        raise ScrapingError(
            f"nexum-core: HTTP {resp.status_code} from {API_URL}: {resp.text[:300]}"
        )

    try:
        data = resp.json()
    except ValueError as e:
        raise ScrapingError(f"nexum-core: response was not JSON: {e}") from e

    return {
        "raw_upload": float(data.get("uploaded", 0)),
        "raw_download": float(data.get("downloaded", 0)),
        "bonus": float(data.get("bonus_points", 0)),
    }
