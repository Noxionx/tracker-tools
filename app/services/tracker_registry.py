from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType


def list_scrapers() -> list[str]:
    """Return all available scraper module names."""

    folder = Path(__file__).resolve().parents[1] / "scrapers"
    return sorted([f.stem for f in folder.glob("*.py") if not f.name.startswith("_")])


def load_scraper(name: str) -> ModuleType:
    """Import and return a scraper module by name."""

    return importlib.import_module(f"app.scrapers.{name}")
