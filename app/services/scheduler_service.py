from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.services.tracker_stats_service import refresh_all_trackers


async def refresh_all_trackers_job() -> None:
    async with SessionLocal() as db:
        await refresh_all_trackers(db)


def build_scheduler(refresh_interval_minutes: int) -> AsyncIOScheduler:
    """Create and configure the scheduler for periodic tracker refresh."""

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        refresh_all_trackers_job,
        "interval",
        minutes=refresh_interval_minutes,
        max_instances=1,
        coalesce=True,
    )
    return scheduler
