from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def directory_size(path: Path) -> int:
    """Compute total size of files under a directory."""

    total = 0
    if not path.exists():
        return 0

    for file_path in path.rglob("*"):
        try:
            if file_path.is_file():
                total += file_path.stat().st_size
        except OSError:
            continue

    return total


def get_storage_status(extra_reserved_bytes: int = 0) -> dict[str, Any]:
    settings = get_settings()
    download_dir = settings.download_dir

    if download_dir is None:
        return {
            "download_dir": None,
            "current_used_bytes": 0,
            "forecast_used_bytes": extra_reserved_bytes,
            "max_storage_bytes": settings.max_storage_bytes,
            "disk_total_bytes": 0,
            "disk_used_bytes": 0,
            "disk_free_bytes": 0,
            "min_free_storage_bytes": settings.min_free_storage_bytes,
            "configured": False,
        }

    usage = shutil.disk_usage(download_dir)
    current_used = directory_size(download_dir)

    return {
        "download_dir": str(download_dir),
        "current_used_bytes": current_used,
        "forecast_used_bytes": current_used + extra_reserved_bytes,
        "max_storage_bytes": settings.max_storage_bytes,
        "disk_total_bytes": usage.total,
        "disk_used_bytes": usage.used,
        "disk_free_bytes": usage.free,
        "min_free_storage_bytes": settings.min_free_storage_bytes,
        "configured": True,
    }


def storage_allowed(
    extra_reserved_bytes: int = 0,
    max_storage_bytes: int | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    """Validate storage constraints for a forecasted reservation."""

    status = get_storage_status(extra_reserved_bytes=extra_reserved_bytes)
    effective_max = max_storage_bytes if max_storage_bytes is not None else status["max_storage_bytes"]

    if effective_max > 0 and status["forecast_used_bytes"] > effective_max:
        return False, "Forecast storage usage would exceed maximum allowed storage", status

    min_free = status["min_free_storage_bytes"]
    if min_free > 0 and status["disk_free_bytes"] - extra_reserved_bytes < min_free:
        return False, "Forecast disk free space would be below minimum free storage", status

    return True, "Storage allowed", status
