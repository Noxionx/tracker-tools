import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def get_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return float(value)


def get_tracker_min_ratio(tracker: str) -> float:
    tracker_key = tracker.upper().replace("-", "_")
    return get_float_env(f"{tracker_key}_MIN_RATIO", get_float_env("DEFAULT_MIN_RATIO", 1.0))


def get_max_storage_bytes() -> int:
    return get_int_env("MAX_STORAGE_BYTES", 0)


def get_min_free_storage_bytes() -> int:
    return get_int_env("MIN_FREE_STORAGE_BYTES", 0)


def get_download_dir() -> Optional[Path]:
    value = os.getenv("DOWNLOAD_DIR")
    if not value:
        return None
    return Path(value)


def get_max_tracker_stats_age_minutes() -> int:
    return get_int_env("MAX_TRACKER_STATS_AGE_MINUTES", 120)


def get_refresh_interval_minutes() -> int:
    return get_int_env("REFRESH_INTERVAL_MINUTES", 60)
