from typing import Optional

from pydantic import BaseModel, Field


class ForecastRequest(BaseModel):
    tracker: str
    torrent: Optional[str] = Field(
        default=None,
        description="Magnet URI, local torrent path, or URL understood by Transmission.",
    )
    size_bytes: Optional[int] = Field(
        default=None,
        description="Optional known torrent size. Recommended for dry-run forecasts.",
    )
    min_ratio: Optional[float] = None
    max_storage_bytes: Optional[int] = None


class AddTorrentRequest(ForecastRequest):
    dry_run: bool = False
    download_dir: Optional[str] = None
    paused: bool = False


class PurgeRequest(BaseModel):
    tracker: Optional[str] = None
    target_ratio: Optional[float] = None
    max_lifetime_hours: Optional[int] = None
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
    torrent_hash: Optional[str] = None
    torrent_name: Optional[str] = None
    torrent_size_bytes: int = 0
