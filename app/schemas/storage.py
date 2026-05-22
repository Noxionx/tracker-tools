from pydantic import BaseModel


class StorageStatusResponse(BaseModel):
    download_dir: str | None
    current_used_bytes: int
    forecast_used_bytes: int
    max_storage_bytes: int
    disk_total_bytes: int
    disk_used_bytes: int
    disk_free_bytes: int
    min_free_storage_bytes: int
    configured: bool
