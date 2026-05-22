from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.dependencies import DBSession
from app.schemas.torrent import AddTorrentRequest, ForecastRequest, PurgeRequest
from app.services.purge_service import purge_torrents
from app.services.torrent_service import check_and_add_torrent, forecast_torrent
from app.services.transmission_service import list_torrents, serialize_torrent

router = APIRouter(tags=["torrents"])


@router.get("/torrents")
async def get_torrents() -> dict[str, Any]:
    torrents = await list_torrents()
    return {"torrents": [serialize_torrent(item) for item in torrents]}


@router.post("/torrents/forecast")
async def forecast(request: ForecastRequest, db: DBSession) -> Any:
    try:
        return await forecast_torrent(db, request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/torrents/check-and-add")
async def check_and_add(request: AddTorrentRequest, db: DBSession) -> Any:
    try:
        return await check_and_add_torrent(db, request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/torrents/purge")
async def purge(request: PurgeRequest) -> Any:
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
