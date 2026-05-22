from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.time import utcnow
from app.models.tracker import TorrentReservation, TrackedTorrent
from app.schemas.torrent import AddTorrentRequest, DecisionResponse, ForecastRequest
from app.services.storage_service import storage_allowed
from app.services.tracker_domain import torrent_belongs_to_tracker
from app.services.tracker_stats_service import ensure_fresh_tracker_stats
from app.services.transmission_service import add_torrent, list_torrents

_tracker_locks: dict[str, asyncio.Lock] = {}


def _get_tracker_lock(tracker: str) -> asyncio.Lock:
    if tracker not in _tracker_locks:
        _tracker_locks[tracker] = asyncio.Lock()
    return _tracker_locks[tracker]


def _tracker_min_ratio(tracker: str) -> float:
    env_key = f"{tracker.upper().replace('-', '_')}_MIN_RATIO"
    import os

    env_value = os.getenv(env_key)
    if env_value:
        return float(env_value)
    return get_settings().default_min_ratio


async def _get_pending_reserved_size(db: AsyncSession, tracker: str) -> int:
    result = await db.execute(
        select(TorrentReservation).where(
            TorrentReservation.tracker_name == tracker,
            TorrentReservation.status == "pending",
        )
    )
    reservations = result.scalars().all()
    return sum(item.size_bytes for item in reservations)


async def _create_reservation(
    db: AsyncSession,
    tracker: str,
    size_bytes: int,
) -> TorrentReservation:
    now = utcnow()
    reservation = TorrentReservation(
        tracker_name=tracker,
        size_bytes=size_bytes,
        status="pending",
        created_at=now,
        expires_at=now + timedelta(minutes=30),
    )
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)
    return reservation


async def _update_reservation_status(
    db: AsyncSession,
    reservation: TorrentReservation,
    status: str,
    torrent_hash: str | None = None,
    name: str | None = None,
) -> None:
    reservation.status = status
    if torrent_hash:
        reservation.torrent_hash = torrent_hash
    if name:
        reservation.name = name
    await db.commit()


async def _track_added_torrent(db: AsyncSession, tracker: str, torrent: Any) -> None:
    now = utcnow()
    tracked = TrackedTorrent(
        tracker_name=tracker,
        torrent_hash=torrent.hash_string,
        transmission_id=torrent.id,
        name=torrent.name,
        size_bytes=torrent.total_size,
        status="added",
        added_at=torrent.added_date or now,
        completed_at=torrent.done_date,
        removed_at=None,
        downloaded_at_add=torrent.downloaded_ever,
        uploaded_at_add=torrent.uploaded_ever,
        created_at=now,
        updated_at=now,
    )
    db.add(tracked)
    await db.commit()


async def _get_active_tracker_deltas(tracker: str) -> tuple[float, float, list[dict[str, Any]]]:
    torrents = await list_torrents()
    upload_delta = 0.0
    download_delta = 0.0
    matched: list[dict[str, Any]] = []

    for torrent in torrents:
        if not torrent_belongs_to_tracker(torrent.trackers, tracker):
            continue

        upload_delta += torrent.uploaded_ever
        download_delta += torrent.downloaded_ever
        matched.append(
            {
                "id": torrent.id,
                "hash": torrent.hash_string,
                "name": torrent.name,
                "size_bytes": torrent.total_size,
                "downloaded_ever": torrent.downloaded_ever,
                "uploaded_ever": torrent.uploaded_ever,
                "ratio": torrent.ratio,
                "status": torrent.status,
            }
        )

    return upload_delta, download_delta, matched


async def forecast_torrent(db: AsyncSession, request: ForecastRequest) -> DecisionResponse:
    tracker = request.tracker
    ratio_override = request.min_ratio
    min_ratio = ratio_override if ratio_override is not None and ratio_override > 0 else _tracker_min_ratio(tracker)
    max_storage_override = (
        request.max_storage_bytes
        if request.max_storage_bytes is not None and request.max_storage_bytes > 0
        else None
    )

    stats = await ensure_fresh_tracker_stats(db, tracker)
    active_upload_delta, active_download_delta, _ = await _get_active_tracker_deltas(tracker)
    pending_reserved_size = await _get_pending_reserved_size(db, tracker)

    candidate_size = int(request.size_bytes or 0)
    candidate_ratio_download = 0 if request.is_freeleech else candidate_size
    forecast_upload = stats.raw_upload + active_upload_delta
    forecast_download = stats.raw_download + active_download_delta + pending_reserved_size + candidate_ratio_download
    if forecast_download > 0:
        forecast_ratio = forecast_upload / forecast_download
    elif forecast_upload > 0:
        forecast_ratio = 999.0
    else:
        forecast_ratio = 0.0

    extra_storage = pending_reserved_size + candidate_size
    storage_ok, storage_reason, storage = storage_allowed(
        extra_reserved_bytes=extra_storage,
        max_storage_bytes=max_storage_override,
    )
    ratio_ok = forecast_ratio >= min_ratio

    if not ratio_ok:
        reason = "Forecast ratio would be below minimum ratio"
    elif not storage_ok:
        reason = storage_reason
    else:
        reason = "Torrent allowed"

    return DecisionResponse(
        allowed=ratio_ok and storage_ok,
        added=False,
        reason=reason,
        tracker=tracker,
        current_ratio=stats.raw_ratio,
        forecast_ratio=forecast_ratio,
        minimum_ratio=min_ratio,
        current_upload=stats.raw_upload,
        current_download=stats.raw_download,
        forecast_upload=forecast_upload,
        forecast_download=forecast_download,
        current_storage_bytes=storage["current_used_bytes"],
        forecast_storage_bytes=storage["forecast_used_bytes"],
        max_storage_bytes=max_storage_override or storage["max_storage_bytes"],
        torrent_hash=None,
        torrent_name=None,
        torrent_size_bytes=candidate_size,
    )


async def admit_torrent(db: AsyncSession, request: AddTorrentRequest) -> DecisionResponse:
    tracker = request.tracker

    async with _get_tracker_lock(tracker):
        decision = await forecast_torrent(db, request)
        if not decision.allowed or request.dry_run:
            return decision

        candidate_size = int(request.size_bytes or 0)
        reservation = await _create_reservation(db, tracker=tracker, size_bytes=candidate_size)

        try:
            download_dir = request.download_dir
            if download_dir is None and get_settings().download_dir is not None:
                download_dir = str(get_settings().download_dir)

            added = await add_torrent(
                torrent=request.torrent,
                download_dir=download_dir,
                paused=request.paused,
            )

            await _update_reservation_status(
                db,
                reservation,
                "added",
                torrent_hash=added.hash_string,
                name=added.name,
            )
            await _track_added_torrent(db, tracker, added)

            decision.added = True
            decision.reason = "Torrent accepted and added to Transmission"
            decision.torrent_hash = added.hash_string
            decision.torrent_name = added.name
            decision.torrent_size_bytes = added.total_size or candidate_size
            return decision
        except Exception as exc:
            await _update_reservation_status(db, reservation, "failed")
            raise RuntimeError(f"Failed to add torrent to Transmission: {exc}") from exc
