from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import DBSession
from app.services.tracker_registry import list_scrapers
from app.services.tracker_stats_service import (
    get_latest_tracker_stats,
    get_tracker_history,
    refresh_tracker,
    serialize_tracker_stats,
)

router = APIRouter(tags=["trackers"])


@router.get("/ratios")
async def get_ratios(db: DBSession) -> dict[str, Any]:
    data: dict[str, Any] = {}

    for tracker in list_scrapers():
        latest = await get_latest_tracker_stats(db, tracker)
        if latest:
            data[tracker] = {
                "ratio": latest.raw_ratio,
                "upload": latest.raw_upload,
                "download": latest.raw_download,
                "bonus": latest.bonus,
                "scraped_at": latest.scraped_at,
                "changed_at": latest.changed_at,
                "error": latest.error,
            }

    return data


@router.get("/trackers/{tracker}/stats")
async def tracker_stats(tracker: str, db: DBSession) -> dict[str, Any]:
    latest = await get_latest_tracker_stats(db, tracker)
    if not latest:
        raise HTTPException(status_code=404, detail=f"No stats found for tracker '{tracker}'")
    return serialize_tracker_stats(latest)


@router.get("/trackers/{tracker}/history")
async def tracker_history(
    tracker: str,
    db: DBSession,
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    history = await get_tracker_history(db, tracker, limit=limit)
    return {"tracker": tracker, "items": [serialize_tracker_stats(item) for item in history]}


@router.post("/trackers/{tracker}/refresh")
async def refresh_tracker_endpoint(tracker: str, db: DBSession) -> dict[str, Any]:
    if tracker not in list_scrapers():
        raise HTTPException(status_code=404, detail=f"Unknown tracker '{tracker}'")

    stats = await refresh_tracker(db, tracker)
    return serialize_tracker_stats(stats)
