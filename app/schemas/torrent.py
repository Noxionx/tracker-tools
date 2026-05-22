from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ForecastRequest(BaseModel):
    tracker: str
    torrent: str | None = Field(
        default=None,
        description="Magnet URI, local torrent path, or URL understood by Transmission.",
    )
    size_bytes: int | None = Field(
        default=None,
        description="Optional known torrent size. Recommended for dry-run forecasts.",
    )
    min_ratio: float | None = None
    max_storage_bytes: int | None = None


class AddTorrentRequest(ForecastRequest):
    dry_run: bool = False
    download_dir: str | None = None
    paused: bool = False


class PurgeRequest(BaseModel):
    tracker: str | None = None
    target_ratio: float | None = None
    max_lifetime_hours: int | None = None
    delete_data: bool = False
    dry_run: bool = True


class DecisionResponse(BaseModel):
    allowed: bool
    added: bool = False
    reason: str
    tracker: str
    current_ratio: float
    forecast_ratio: float
    minimum_ratio: float
    current_upload: float
    current_download: float
    forecast_upload: float
    forecast_download: float
    current_storage_bytes: int
    forecast_storage_bytes: int
    max_storage_bytes: int
    torrent_hash: str | None = None
    torrent_name: str | None = None
    torrent_size_bytes: int = 0


class TorrentResponse(BaseModel):
    id: int
    hash: str
    name: str
    size_bytes: int
    downloaded_ever: float
    uploaded_ever: float
    ratio: float
    status: str
    added_date: datetime | None = None
    done_date: datetime | None = None
    download_dir: str | None = None
    trackers: list[str]


class TorrentListResponse(BaseModel):
    torrents: list[TorrentResponse]


class PurgeTorrentResult(BaseModel):
    id: int
    hash: str
    name: str
    ratio: float
    age_hours: float | None
    size_bytes: int
    reasons: list[str]


class PurgeResponse(BaseModel):
    dry_run: bool
    delete_data: bool
    matched_count: int
    total_reclaimable_bytes: int
    torrents: list[PurgeTorrentResult]
