from typing import Any

from fastapi import APIRouter

from app.services.tracker_registry import list_scrapers

router = APIRouter(tags=["system"])


@router.get("/")
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
            "/torrents/admit",
            "/torrents/purge",
            "/storage",
        ],
    }


@router.get("/trackers")
async def trackers() -> dict[str, list[str]]:
    return {"trackers": list_scrapers()}
