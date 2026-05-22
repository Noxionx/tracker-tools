from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

from app.core.config import get_settings


def list_available_scrapers() -> list[str]:
    """Return all discovered scraper module names from the package."""

    folder = Path(__file__).resolve().parents[1] / "scrapers"
    return sorted([f.stem for f in folder.glob("*.py") if not f.name.startswith("_")])


def list_scrapers() -> list[str]:
    """Return active scraper names based on explicit config or credential discovery."""

    available = list_available_scrapers()
    settings = get_settings()

    # Explicit allow-list has priority when provided.
    if settings.scrapers_enabled:
        explicit = {item.strip() for item in settings.scrapers_enabled}
        return sorted([name for name in available if name in explicit])

    active: list[str] = []
    for name in available:
        module = load_scraper(name)
        is_enabled = getattr(module, "is_enabled", None)
        if callable(is_enabled) and is_enabled(settings):
            active.append(name)
    return sorted(active)


def load_scraper(name: str) -> ModuleType:
    """Import and return a scraper module by name."""

    return importlib.import_module(f"app.scrapers.{name}")
