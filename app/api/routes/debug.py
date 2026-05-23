from typing import Any

from fastapi import APIRouter
from sqlalchemy import desc, select

from app.api.dependencies import DBSession
from app.models.tracker import TrackerStatsSnapshot
from app.schemas.torrent import ForecastRequest
from app.services.torrent_service import build_forecast_breakdown
from app.services.tracker_stats_service import serialize_tracker_stats

router = APIRouter(tags=["debug"])


@router.get("/debug/latest-snapshots")
async def latest_snapshots(db: DBSession) -> dict[str, Any]:
    result = await db.execute(
        select(TrackerStatsSnapshot).order_by(desc(TrackerStatsSnapshot.scraped_at)).limit(20)
    )
    return {"items": [serialize_tracker_stats(item) for item in result.scalars().all()]}


@router.post("/debug/torrents/forecast-breakdown")
async def forecast_breakdown(request: ForecastRequest, db: DBSession) -> dict[str, Any]:
    return await build_forecast_breakdown(db, request)
