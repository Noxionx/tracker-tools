from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return a timezone-aware UTC datetime."""

    return datetime.now(timezone.utc)


def ensure_utc_aware(value: datetime | None) -> datetime | None:
    """Normalize potentially naive datetimes to timezone-aware UTC values."""

    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
