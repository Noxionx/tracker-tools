import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from database_initialization import AsyncSessionLocal, get_db, init_db
from tracker_stats_service import TrackerStatsSnapshot
from torrent_reservation_manager import check_and_add_torrent, forecast_torrent
from torrent_purge_service import purge_torrents
from torrent_management_requests import AddTorrentRequest, ForecastRequest, PurgeRequest
from enviroment_variable_utilities import get_refresh_interval_minutes
from storage_management import get_storage_status
from tracker_stats_service import (
    get_latest_tracker_stats,
    get_tracker_history,
    refresh_all_trackers,
    refresh_tracker,
    serialize_tracker_stats,
)
from torrent_manager import list_torrents, serialize_torrent
from util import list_scrappers

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")


async def update_all() -> None:
    async with AsyncSessionLocal() as db:
        await refresh_all_trackers(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    asyncio.create_task(update_all())

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        update_all,
        "interval",
        minutes=get_refresh_interval_minutes(),
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

    yield

    scheduler.shutdown()


app = FastAPI(
    title="Tracker Tools API",
    description="Tracker ratio scraper, Transmission admission controller, forecaster and purge API.",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "message": "Tracker Tools API is running",
        "endpoints": [
            "/ratios",
            "/trackers",
            "/trackers/{tracker}/stats",
            "/trackers/{tracker}/history",
            "/trackers/{tracker}/refresh",
            "/torrents",
            "/torrents/forecast",
            "/torrents/check-and-add",
            "/torrents/purge",
            "/storage",
        ],
    }


@app.get("/trackers")
async def trackers() -> dict[str, Any]:
    return {"trackers": list_scrappers()}


@app.get("/ratios")
async def get_ratios(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    data: dict[str, Any] = {}

    for tracker in list_scrappers():
        latest = await get_latest_tracker_stats(db, tracker)
        if latest:
            data[tracker] = {
                "ratio": latest.raw_ratio,
                "upload": latest.raw_upload,
                "download": latest.raw_download,
                "bonus": latest.bonus,
                "scraped_at": latest.scraped_at.isoformat(),
                "changed_at": latest.changed_at.isoformat(),
                "error": latest.error,
            }

    return data


@app.get("/trackers/{tracker}/stats")
async def tracker_stats(
    tracker: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    latest = await get_latest_tracker_stats(db, tracker)

    if not latest:
        raise HTTPException(status_code=404, detail=f"No stats found for tracker '{tracker}'")

    return serialize_tracker_stats(latest)


@app.get("/trackers/{tracker}/history")
async def tracker_history(
    tracker: str,
    limit: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    history = await get_tracker_history(db, tracker, limit=limit)
    return {
        "tracker": tracker,
        "items": [serialize_tracker_stats(item) for item in history],
    }


@app.post("/trackers/{tracker}/refresh")
async def refresh_tracker_endpoint(
    tracker: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if tracker not in list_scrappers():
        raise HTTPException(status_code=404, detail=f"Unknown tracker '{tracker}'")

    stats = await refresh_tracker(db, tracker)
    return serialize_tracker_stats(stats)


@app.get("/torrents")
async def get_torrents() -> dict[str, Any]:
    torrents = await list_torrents()
    return {"torrents": [serialize_torrent(item) for item in torrents]}


@app.post("/torrents/forecast")
async def forecast(
    request: ForecastRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await forecast_torrent(db, request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/torrents/check-and-add")
async def check_and_add(
    request: AddTorrentRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await check_and_add_torrent(db, request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/torrents/purge")
async def purge(request: PurgeRequest):
    if request.target_ratio is None and request.max_lifetime_hours is None:
        raise HTTPException(
            status_code=400,
            detail="At least one purge condition is required: target_ratio or max_lifetime_hours",
        )

    try:
        return await purge_torrents(
            tracker=request.tracker,
            target_ratio=request.target_ratio,
            max_lifetime_hours=request.max_lifetime_hours,
            delete_data=request.delete_data,
            dry_run=request.dry_run,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/storage")
async def storage() -> dict[str, Any]:
    return get_storage_status()


@app.get("/debug/latest-snapshots")
async def latest_snapshots(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(TrackerStatsSnapshot)
        .order_by(desc(TrackerStatsSnapshot.scraped_at))
        .limit(20)
    )

    return {
        "items": [
            serialize_tracker_stats(item)
            for item in result.scalars().all()
        ]
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8679)
