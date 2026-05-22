from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database_initialization import Base


class TrackerStatsSnapshot(Base):
    __tablename__ = "tracker_stats_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tracker_name: Mapped[str] = mapped_column(String(128), index=True)
    raw_upload: Mapped[float] = mapped_column(Float, default=0)
    raw_download: Mapped[float] = mapped_column(Float, default=0)
    raw_ratio: Mapped[float] = mapped_column(Float, default=0)
    bonus: Mapped[float] = mapped_column(Float, default=0)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class TrackedTorrent(Base):
    __tablename__ = "tracked_torrents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tracker_name: Mapped[str] = mapped_column(String(128), index=True)
    torrent_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    transmission_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(64), index=True, default="added")
    added_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    removed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    downloaded_at_add: Mapped[float] = mapped_column(Float, default=0)
    uploaded_at_add: Mapped[float] = mapped_column(Float, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class TorrentReservation(Base):
    __tablename__ = "torrent_reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tracker_name: Mapped[str] = mapped_column(String(128), index=True)
    torrent_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    name: Mapped[str] = mapped_column(Text, default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(64), index=True, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
