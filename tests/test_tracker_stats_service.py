from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.core.time import utcnow
from app.services.tracker_stats_service import compute_ratio, ensure_fresh_tracker_stats


def test_compute_ratio_with_download() -> None:
    assert compute_ratio(50.0, 10.0) == 5.0


def test_compute_ratio_with_upload_only() -> None:
    assert compute_ratio(10.0, 0.0) == 999.0


def test_compute_ratio_with_zero_values() -> None:
    assert compute_ratio(0.0, 0.0) == 0.0


@pytest.mark.asyncio
async def test_ensure_fresh_tracker_stats_accepts_naive_scraped_at(monkeypatch) -> None:
    latest = SimpleNamespace(scraped_at=utcnow().replace(tzinfo=None), error=None)

    async def fake_get_latest_tracker_stats(db, tracker):
        return latest

    async def fake_refresh_tracker(db, tracker):
        raise AssertionError("refresh_tracker should not be called for fresh stats")

    monkeypatch.setattr(
        "app.services.tracker_stats_service.get_latest_tracker_stats",
        fake_get_latest_tracker_stats,
    )
    monkeypatch.setattr("app.services.tracker_stats_service.refresh_tracker", fake_refresh_tracker)

    result = await ensure_fresh_tracker_stats(db=object(), tracker="c411")

    assert result is latest


@pytest.mark.asyncio
async def test_ensure_fresh_tracker_stats_raises_when_latest_has_error(monkeypatch) -> None:
    latest = SimpleNamespace(
        scraped_at=utcnow().replace(tzinfo=None) - timedelta(minutes=1),
        error="scraper down",
    )

    async def fake_get_latest_tracker_stats(db, tracker):
        return latest

    async def fake_refresh_tracker(db, tracker):
        raise AssertionError("refresh_tracker should not be called for recent errored stats")

    monkeypatch.setattr(
        "app.services.tracker_stats_service.get_latest_tracker_stats",
        fake_get_latest_tracker_stats,
    )
    monkeypatch.setattr("app.services.tracker_stats_service.refresh_tracker", fake_refresh_tracker)

    with pytest.raises(RuntimeError, match="Latest tracker stats contain error"):
        await ensure_fresh_tracker_stats(db=object(), tracker="c411")
