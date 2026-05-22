from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime

from transmission_rpc import Client

from app.core.config import get_settings
from app.core.time import ensure_utc_aware


@dataclass(slots=True)
class TorrentInfo:
    id: int
    hash_string: str
    name: str
    total_size: int
    downloaded_ever: float
    uploaded_ever: float
    ratio: float
    status: str
    added_date: datetime | None
    done_date: datetime | None
    download_dir: str | None
    trackers: list[str]


def _connect() -> Client:
    settings = get_settings()
    kwargs: dict[str, object] = {
        "host": settings.transmission_host,
        "port": settings.transmission_port,
        "path": settings.transmission_path,
    }

    if settings.transmission_username:
        kwargs["username"] = settings.transmission_username
    if settings.transmission_password:
        kwargs["password"] = settings.transmission_password

    return Client(**kwargs)


def _extract_trackers(torrent: object) -> list[str]:
    trackers: list[str] = []

    tracker_stats = getattr(torrent, "tracker_stats", None)
    if tracker_stats:
        trackers.extend(str(item.announce) for item in tracker_stats if getattr(item, "announce", None))

    tracker_list = getattr(torrent, "trackers", None)
    if tracker_list:
        trackers.extend(str(item.announce) for item in tracker_list if getattr(item, "announce", None))

    return trackers


def _to_info(torrent: object) -> TorrentInfo:
    added_date = getattr(torrent, "added_date", None) or getattr(torrent, "addedDate", None)
    done_date = getattr(torrent, "done_date", None) or getattr(torrent, "doneDate", None)

    return TorrentInfo(
        id=int(getattr(torrent, "id")),
        hash_string=str(getattr(torrent, "hash_string", "") or getattr(torrent, "hashString", "")),
        name=str(getattr(torrent, "name", "")),
        total_size=int(getattr(torrent, "total_size", 0) or getattr(torrent, "totalSize", 0) or 0),
        downloaded_ever=float(
            getattr(torrent, "downloaded_ever", 0) or getattr(torrent, "downloadedEver", 0) or 0
        ),
        uploaded_ever=float(
            getattr(torrent, "uploaded_ever", 0) or getattr(torrent, "uploadedEver", 0) or 0
        ),
        ratio=float(getattr(torrent, "ratio", 0) or 0),
        status=str(getattr(torrent, "status", "")),
        added_date=ensure_utc_aware(added_date),
        done_date=ensure_utc_aware(done_date),
        download_dir=getattr(torrent, "download_dir", None) or getattr(torrent, "downloadDir", None),
        trackers=_extract_trackers(torrent),
    )


async def list_torrents() -> list[TorrentInfo]:
    def run() -> list[TorrentInfo]:
        client = _connect()
        return [_to_info(torrent) for torrent in client.get_torrents()]

    return await asyncio.to_thread(run)


async def add_torrent(torrent: str, download_dir: str | None = None, paused: bool = False) -> TorrentInfo:
    def run() -> TorrentInfo:
        client = _connect()
        added = client.add_torrent(torrent=torrent, download_dir=download_dir, paused=paused)
        return _to_info(client.get_torrent(added.id))

    return await asyncio.to_thread(run)


async def remove_torrent(torrent_id: int, delete_data: bool) -> None:
    def run() -> None:
        client = _connect()
        client.remove_torrent(ids=[torrent_id], delete_data=delete_data)

    await asyncio.to_thread(run)


def serialize_torrent(info: TorrentInfo) -> dict[str, object]:
    return {
        "id": info.id,
        "hash": info.hash_string,
        "name": info.name,
        "size_bytes": info.total_size,
        "downloaded_ever": info.downloaded_ever,
        "uploaded_ever": info.uploaded_ever,
        "ratio": info.ratio,
        "status": info.status,
        "added_date": info.added_date,
        "done_date": info.done_date,
        "download_dir": info.download_dir,
        "trackers": info.trackers,
    }
