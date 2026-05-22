from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.core.exceptions import UnknownTrackerError
from app.services.scraper_service import get_stats
from app.services.tracker_registry import list_available_scrapers, list_scrapers

SCRAPER_ENV_KEYS = [
    "SCRAPERS_ENABLED",
    "C411_USER",
    "C411_PASS",
    "TORR9_USER",
    "TOR9_USER",
    "TORR9_PASSWORD",
    "TORR9_PASS",
    "TOR9_PASS",
    "CRAZYSPIRITS_COOKIE",
    "GEMINI_TOKEN",
    "GFREE_TOKEN",
    "LACALE_USER",
    "LACALE_PASS",
    "NEXUM_TOKEN",
    "NOSTRADAMUS_PRIVATE_KEY",
    "NOSTRADAMUS_API_KEY",
    "NOSTRADAMUS_PRIVATE_TICKET",
    "TEAMFLIX_TOKEN",
    "TOS_TOKEN",
    "TL_USER",
    "TL_PASS",
    "TR4KER_TOKEN",
    "TR4KER_API_KEY",
]


def _reset_scraper_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in SCRAPER_ENV_KEYS:
        monkeypatch.setenv(key, "")
    get_settings.cache_clear()


def test_list_available_scrapers_discovers_modules() -> None:
    available = list_available_scrapers()

    assert "c411" in available
    assert "torr9" in available
    assert "tr4ker" in available


def test_default_no_scraper_is_active_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_scraper_env(monkeypatch)

    assert list_scrapers() == []


def test_scraper_auto_activation_from_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_scraper_env(monkeypatch)
    monkeypatch.setenv("GEMINI_TOKEN", "demo-token")
    get_settings.cache_clear()

    active = list_scrapers()

    assert "gemini" in active
    assert "c411" not in active


def test_explicit_scraper_enable_list_has_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_scraper_env(monkeypatch)
    monkeypatch.setenv("SCRAPERS_ENABLED", "torr9,gemini")
    get_settings.cache_clear()

    assert list_scrapers() == ["gemini", "torr9"]


@pytest.mark.asyncio
async def test_disabled_scraper_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_scraper_env(monkeypatch)

    with pytest.raises(UnknownTrackerError, match="currently disabled"):
        await get_stats("gemini")
