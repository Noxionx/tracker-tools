from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TrackerStatsResponse(BaseModel):
    """Serialized tracker statistics returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    tracker: str
    ratio: float
    upload: float
    download: float
    bonus: float
    scraped_at: datetime
    changed_at: datetime
    error: str | None = None


class TrackerHistoryResponse(BaseModel):
    tracker: str
    items: list[TrackerStatsResponse]


class TrackerListResponse(BaseModel):
    trackers: list[str]


class RatiosResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
