from datetime import datetime, timezone
from typing import Any, Optional

from tracker_domain_utils import torrent_belongs_to_tracker
from torrent_manager import list_torrents, remove_torrent


def _age_hours(added_date: Any) -> Optional[float]:
    if not added_date:
        return None

    now = datetime.now(timezone.utc)

    if added_date.tzinfo is None:
        added_date = added_date.replace(tzinfo=timezone.utc)

    return (now - added_date).total_seconds() / 3600


async def purge_torrents(
    tracker: Optional[str],
    target_ratio: Optional[float],
    max_lifetime_hours: Optional[int],
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

        if not reasons:
            continue

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
