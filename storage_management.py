import shutil
from pathlib import Path
from typing import Any

from enviroment_variable_utilities import get_download_dir, get_max_storage_bytes, get_min_free_storage_bytes


def directory_size(path: Path) -> int:
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
    download_dir = get_download_dir()
    max_storage_bytes = get_max_storage_bytes()
    min_free_storage_bytes = get_min_free_storage_bytes()

    if download_dir is None:
        return {
            "download_dir": None,
            "current_used_bytes": 0,
            "forecast_used_bytes": extra_reserved_bytes,
            "max_storage_bytes": max_storage_bytes,
            "disk_total_bytes": 0,
            "disk_used_bytes": 0,
            "disk_free_bytes": 0,
            "min_free_storage_bytes": min_free_storage_bytes,
            "configured": False,
        }

    usage = shutil.disk_usage(download_dir)
    current_used = directory_size(download_dir)
    forecast_used = current_used + extra_reserved_bytes

    return {
        "download_dir": str(download_dir),
        "current_used_bytes": current_used,
        "forecast_used_bytes": forecast_used,
        "max_storage_bytes": max_storage_bytes,
        "disk_total_bytes": usage.total,
        "disk_used_bytes": usage.used,
        "disk_free_bytes": usage.free,
        "min_free_storage_bytes": min_free_storage_bytes,
        "configured": True,
    }


def storage_allowed(extra_reserved_bytes: int = 0, max_storage_bytes: int | None = None) -> tuple[bool, str, dict[str, Any]]:
    status = get_storage_status(extra_reserved_bytes=extra_reserved_bytes)

    effective_max = max_storage_bytes if max_storage_bytes is not None else status["max_storage_bytes"]

    if effective_max > 0 and status["forecast_used_bytes"] > effective_max:
        return False, "Forecast storage usage would exceed maximum allowed storage", status

    min_free = status["min_free_storage_bytes"]
    if min_free > 0 and status["disk_free_bytes"] - extra_reserved_bytes < min_free:
        return False, "Forecast disk free space would be below minimum free storage", status

    return True, "Storage allowed", status
