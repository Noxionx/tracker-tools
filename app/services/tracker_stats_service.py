from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.time import ensure_utc_aware, utcnow
from app.models.tracker import TrackerStatsSnapshot
from app.services.scraper_service import get_stats
from app.services.tracker_registry import list_scrapers

logger = logging.getLogger(__name__)


def compute_ratio(raw_upload: float, raw_download: float) -> float:
    if raw_download > 0:
        return raw_upload / raw_download
    if raw_upload > 0:
        return 999.0
    return 0.0


async def get_latest_tracker_stats(db: AsyncSession, tracker: str) -> TrackerStatsSnapshot | None:
    result = await db.execute(
        select(TrackerStatsSnapshot)
        .where(TrackerStatsSnapshot.tracker_name == tracker)
        .order_by(desc(TrackerStatsSnapshot.scraped_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def save_tracker_stats(
    db: AsyncSession,
    tracker: str,
    stats: dict[str, Any],
    error: str | None = None,
) -> TrackerStatsSnapshot:
    now = utcnow()
    raw_upload = float(stats.get("raw_upload", 0))
    raw_download = float(stats.get("raw_download", 0))
    raw_ratio = compute_ratio(raw_upload, raw_download)
    bonus = float(stats.get("bonus", 0))

    previous = await get_latest_tracker_stats(db, tracker)
    changed_at = now
    if previous:
        same_values = (
            previous.raw_upload == raw_upload
            and previous.raw_download == raw_download
            and previous.raw_ratio == raw_ratio
            and previous.bonus == bonus
        )
        if same_values:
            changed_at = previous.changed_at

    snapshot = TrackerStatsSnapshot(
        tracker_name=tracker,
        raw_upload=raw_upload,
        raw_download=raw_download,
        raw_ratio=raw_ratio,
        bonus=bonus,
        scraped_at=now,
        changed_at=changed_at,
        error=error,
    )

    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    return snapshot


async def refresh_tracker(db: AsyncSession, tracker: str) -> TrackerStatsSnapshot:
    logger.info("Refreshing stats for tracker: %s", tracker)
    try:
        stats = await get_stats(tracker)
        return await save_tracker_stats(db, tracker, stats)
    except Exception as exc:
        logger.error("Scraper error for %s: %s", tracker, exc)
        return await save_tracker_stats(
            db,
            tracker,
            {"raw_upload": 0.0, "raw_download": 0.0, "bonus": 0.0},
            error=str(exc),
        )


async def refresh_all_trackers(db: AsyncSession) -> None:
    for tracker in list_scrapers():
        await refresh_tracker(db, tracker)


async def ensure_fresh_tracker_stats(db: AsyncSession, tracker: str) -> TrackerStatsSnapshot:
    latest = await get_latest_tracker_stats(db, tracker)
    max_age = timedelta(minutes=get_settings().max_tracker_stats_age_minutes)

    if latest is None:
        return await refresh_tracker(db, tracker)

    scraped_at = ensure_utc_aware(latest.scraped_at)
    if scraped_at is None:
        raise RuntimeError("Latest tracker stats have no scraped_at timestamp")

    if utcnow() - scraped_at > max_age:
        refreshed = await refresh_tracker(db, tracker)
        if refreshed.error:
            raise RuntimeError(f"Tracker stats are stale and refresh failed: {refreshed.error}")
        return refreshed

    if latest.error:
        raise RuntimeError(f"Latest tracker stats contain error: {latest.error}")

    return latest


async def get_tracker_history(db: AsyncSession, tracker: str, limit: int = 100) -> list[TrackerStatsSnapshot]:
    result = await db.execute(
        select(TrackerStatsSnapshot)
        .where(TrackerStatsSnapshot.tracker_name == tracker)
        .order_by(desc(TrackerStatsSnapshot.scraped_at))
        .limit(limit)
    )
    return list(result.scalars().all())


def serialize_tracker_stats(row: TrackerStatsSnapshot) -> dict[str, Any]:
    return {
        "tracker": row.tracker_name,
        "ratio": row.raw_ratio,
        "upload": row.raw_upload,
        "download": row.raw_download,
        "bonus": row.bonus,
        "scraped_at": row.scraped_at,
        "changed_at": row.changed_at,
        "error": row.error,
    }
