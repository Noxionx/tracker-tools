from __future__ import annotations

import logging
from typing import Any

from app.core.exceptions import ScrapingError, UnknownTrackerError
from app.services.tracker_registry import list_scrapers, load_scraper

logger = logging.getLogger(__name__)


async def get_stats(tracker: str, headless: bool = True) -> dict[str, Any]:
    """Fetch tracker statistics from a configured scraper implementation."""

    if tracker not in list_scrapers():
        raise UnknownTrackerError(f"Unknown tracker {tracker}")

    try:
        scraper_module = load_scraper(tracker)
        return await scraper_module.get_stats(headless=headless)
    except Exception as exc:
        logger.error("Error while scraping %s: %s", tracker, exc)
        raise ScrapingError(str(exc)) from exc
