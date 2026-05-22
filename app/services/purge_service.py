from __future__ import annotations

from typing import Any

from app.core.time import ensure_utc_aware, utcnow
from app.services.tracker_domain import torrent_belongs_to_tracker
from app.services.transmission_service import list_torrents, remove_torrent


def _age_hours(added_date: Any) -> float | None:
    if not added_date:
        return None

    added_date = ensure_utc_aware(added_date)
    if added_date is None:
        return None

    return (utcnow() - added_date).total_seconds() / 3600


async def purge_torrents(
    tracker: str | None,
    target_ratio: float | None,
    max_lifetime_hours: int | None,
    delete_data: bool,
    dry_run: bool,
) -> dict[str, Any]:
    torrents = await list_torrents()
    matched: list[dict[str, Any]] = []

    for torrent in torrents:
        if tracker and not torrent_belongs_to_tracker(torrent.trackers, tracker):
            continue

        reasons: list[str] = []
        if target_ratio is not None and torrent.ratio >= target_ratio:
            reasons.append("ratio_above_target")

        age = _age_hours(torrent.added_date)
        if max_lifetime_hours is not None and age is not None and age >= max_lifetime_hours:
            reasons.append("lifetime_exceeded")

        if reasons:
            matched.append(
                {
                    "id": torrent.id,
                    "hash": torrent.hash_string,
                    "name": torrent.name,
                    "ratio": torrent.ratio,
                    "age_hours": age,
                    "size_bytes": torrent.total_size,
                    "reasons": reasons,
                }
            )

    if not dry_run:
        for item in matched:
            await remove_torrent(item["id"], delete_data=delete_data)

    return {
        "dry_run": dry_run,
        "delete_data": delete_data,
        "matched_count": len(matched),
        "total_reclaimable_bytes": sum(item["size_bytes"] for item in matched),
        "torrents": matched,
    }
