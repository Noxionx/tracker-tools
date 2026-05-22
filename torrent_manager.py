import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from dotenv import load_dotenv
from transmission_rpc import Client

load_dotenv()


@dataclass
class TorrentInfo:
    id: int
    hash_string: str
    name: str
    total_size: int
    downloaded_ever: float
    uploaded_ever: float
    ratio: float
    status: str
    added_date: Optional[datetime]
    done_date: Optional[datetime]
    download_dir: Optional[str]
    trackers: list[str]


def _connect() -> Client:
    kwargs: dict[str, Any] = {
        "host": os.getenv("TRANSMISSION_HOST", "localhost"),
        "port": int(os.getenv("TRANSMISSION_PORT", "9091")),
        "path": os.getenv("TRANSMISSION_PATH", "/transmission/rpc"),
    }

    username = os.getenv("TRANSMISSION_USERNAME")
    password = os.getenv("TRANSMISSION_PASSWORD")

    if username:
        kwargs["username"] = username
    if password:
        kwargs["password"] = password

    return Client(**kwargs)


def _extract_trackers(torrent: Any) -> list[str]:
    trackers: list[str] = []

    tracker_stats = getattr(torrent, "tracker_stats", None)
    if tracker_stats:
        for tracker in tracker_stats:
            announce = getattr(tracker, "announce", None)
            if announce:
                trackers.append(str(announce))

    tracker_list = getattr(torrent, "trackers", None)
    if tracker_list:
        for tracker in tracker_list:
            announce = getattr(tracker, "announce", None)
            if announce:
                trackers.append(str(announce))

    return trackers


def _to_info(torrent: Any) -> TorrentInfo:
    return TorrentInfo(
        id=int(getattr(torrent, "id")),
        hash_string=str(getattr(torrent, "hash_string", "") or getattr(torrent, "hashString", "")),
        name=str(getattr(torrent, "name", "")),
        total_size=int(getattr(torrent, "total_size", 0) or getattr(torrent, "totalSize", 0) or 0),
        downloaded_ever=float(getattr(torrent, "downloaded_ever", 0) or getattr(torrent, "downloadedEver", 0) or 0),
        uploaded_ever=float(getattr(torrent, "uploaded_ever", 0) or getattr(torrent, "uploadedEver", 0) or 0),
        ratio=float(getattr(torrent, "ratio", 0) or 0),
        status=str(getattr(torrent, "status", "")),
        added_date=getattr(torrent, "added_date", None) or getattr(torrent, "addedDate", None),
        done_date=getattr(torrent, "done_date", None) or getattr(torrent, "doneDate", None),
        download_dir=getattr(torrent, "download_dir", None) or getattr(torrent, "downloadDir", None),
        trackers=_extract_trackers(torrent),
    )


async def list_torrents() -> list[TorrentInfo]:
    def run() -> list[TorrentInfo]:
        client = _connect()
        torrents = client.get_torrents()
        return [_to_info(torrent) for torrent in torrents]

    return await asyncio.to_thread(run)


async def add_torrent(
    torrent: str,
    download_dir: Optional[str] = None,
    paused: bool = False,
) -> TorrentInfo:
    def run() -> TorrentInfo:
        client = _connect()
        added = client.add_torrent(
            torrent=torrent,
            download_dir=download_dir,
            paused=paused,
        )
        torrent_obj = client.get_torrent(added.id)
        return _to_info(torrent_obj)

    return await asyncio.to_thread(run)


async def remove_torrent(
    torrent_id: int,
    delete_data: bool,
) -> None:
    def run() -> None:
        client = _connect()
        client.remove_torrent(ids=[torrent_id], delete_data=delete_data)

    await asyncio.to_thread(run)


async def start_torrent(torrent_id: int) -> None:
    def run() -> None:
        client = _connect()
        client.start_torrent(ids=[torrent_id])

    await asyncio.to_thread(run)


async def stop_torrent(torrent_id: int) -> None:
    def run() -> None:
        client = _connect()
        client.stop_torrent(ids=[torrent_id])

    await asyncio.to_thread(run)


def serialize_torrent(info: TorrentInfo) -> dict[str, Any]:
    return {
        "id": info.id,
        "hash": info.hash_string,
        "name": info.name,
        "size_bytes": info.total_size,
        "downloaded_ever": info.downloaded_ever,
        "uploaded_ever": info.uploaded_ever,
        "ratio": info.ratio,
        "status": info.status,
        "added_date": info.added_date.isoformat() if info.added_date else None,
        "done_date": info.done_date.isoformat() if info.done_date else None,
        "download_dir": info.download_dir,
        "trackers": info.trackers,
    }
