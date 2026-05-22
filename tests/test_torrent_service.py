from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models.tracker import TorrentReservation, TrackedTorrent
from app.schemas.torrent import AddTorrentRequest, DecisionResponse, ForecastRequest
from app.services.torrent_service import admit_torrent, forecast_torrent


@pytest.mark.asyncio
async def test_admit_torrent_dry_run_returns_decision_without_adding(monkeypatch) -> None:
    async def fake_forecast(_db, _request):
        return DecisionResponse(
            allowed=True,
            added=False,
            reason="ok",
            tracker="c411",
            current_ratio=2.0,
            forecast_ratio=1.9,
            minimum_ratio=1.0,
            current_upload=100.0,
            current_download=50.0,
            forecast_upload=100.0,
            forecast_download=53.0,
            current_storage_bytes=100,
            forecast_storage_bytes=120,
            max_storage_bytes=0,
        )

    monkeypatch.setattr("app.services.torrent_service.forecast_torrent", fake_forecast)

    request = AddTorrentRequest(
        tracker="c411",
        torrent="magnet:?xt=urn:btih:abc",
        dry_run=True,
    )

    decision = await admit_torrent(db=None, request=request)

    assert decision.allowed is True
    assert decision.added is False


@pytest.mark.asyncio
async def test_admit_torrent_success_persists_reservation_and_tracking(db_session_factory, monkeypatch) -> None:
    async def fake_forecast(_db, request):
        return DecisionResponse(
            allowed=True,
            added=False,
            reason="ok",
            tracker=request.tracker,
            current_ratio=2.0,
            forecast_ratio=1.7,
            minimum_ratio=1.0,
            current_upload=100.0,
            current_download=50.0,
            forecast_upload=100.0,
            forecast_download=59.0,
            current_storage_bytes=100,
            forecast_storage_bytes=159,
            max_storage_bytes=0,
        )

    async def fake_add_torrent(*, torrent: str, download_dir: str | None, paused: bool):
        assert torrent.startswith("magnet:")
        assert download_dir == "/tmp"
        assert paused is False
        return SimpleNamespace(
            hash_string="hash123",
            id=42,
            name="Example Torrent",
            total_size=1234,
            added_date=None,
            done_date=None,
            downloaded_ever=10.0,
            uploaded_ever=20.0,
        )

    monkeypatch.setattr("app.services.torrent_service.forecast_torrent", fake_forecast)
    monkeypatch.setattr("app.services.torrent_service.add_torrent", fake_add_torrent)

    request = AddTorrentRequest(
        tracker="c411",
        torrent="magnet:?xt=urn:btih:abc",
        dry_run=False,
        download_dir="/tmp",
        paused=False,
        size_bytes=1234,
    )

    async with db_session_factory() as session:
        decision = await admit_torrent(session, request)

    assert decision.added is True
    assert decision.torrent_hash == "hash123"

    async with db_session_factory() as session:
        reservations = (await session.execute(select(TorrentReservation))).scalars().all()
        tracked = (await session.execute(select(TrackedTorrent))).scalars().all()

    assert len(reservations) == 1
    assert reservations[0].status == "added"
    assert reservations[0].torrent_hash == "hash123"
    assert len(tracked) == 1
    assert tracked[0].torrent_hash == "hash123"


@pytest.mark.asyncio
async def test_admit_torrent_failure_marks_reservation_failed(db_session_factory, monkeypatch) -> None:
    async def fake_forecast(_db, request):
        return DecisionResponse(
            allowed=True,
            added=False,
            reason="ok",
            tracker=request.tracker,
            current_ratio=2.0,
            forecast_ratio=1.7,
            minimum_ratio=1.0,
            current_upload=100.0,
            current_download=50.0,
            forecast_upload=100.0,
            forecast_download=59.0,
            current_storage_bytes=100,
            forecast_storage_bytes=159,
            max_storage_bytes=0,
        )

    async def fake_add_torrent(*, torrent: str, download_dir: str | None, paused: bool):
        raise RuntimeError("transmission unavailable")

    monkeypatch.setattr("app.services.torrent_service.forecast_torrent", fake_forecast)
    monkeypatch.setattr("app.services.torrent_service.add_torrent", fake_add_torrent)

    request = AddTorrentRequest(
        tracker="c411",
        torrent="magnet:?xt=urn:btih:abc",
        dry_run=False,
        download_dir="/tmp",
        paused=False,
        size_bytes=1234,
    )

    async with db_session_factory() as session:
        with pytest.raises(RuntimeError, match="Failed to add torrent"):
            await admit_torrent(session, request)

    async with db_session_factory() as session:
        reservations = (await session.execute(select(TorrentReservation))).scalars().all()
        tracked = (await session.execute(select(TrackedTorrent))).scalars().all()

    assert len(reservations) == 1
    assert reservations[0].status == "failed"
    assert len(tracked) == 0


@pytest.mark.asyncio
async def test_forecast_torrent_zero_overrides_fall_back_to_config(monkeypatch) -> None:
    async def fake_ensure_fresh_tracker_stats(_db, _tracker):
        return SimpleNamespace(raw_upload=100.0, raw_download=50.0, raw_ratio=2.0)

    async def fake_get_active_tracker_deltas(_tracker):
        return 0.0, 0.0, []

    async def fake_get_pending_reserved_size(_db, _tracker):
        return 0

    observed: dict[str, int | None] = {"max_storage_bytes": -1}

    def fake_storage_allowed(*, extra_reserved_bytes: int, max_storage_bytes: int | None):
        assert extra_reserved_bytes == 0
        observed["max_storage_bytes"] = max_storage_bytes
        return True, "Storage allowed", {
            "current_used_bytes": 10,
            "forecast_used_bytes": 10,
            "max_storage_bytes": 999,
        }

    monkeypatch.setattr("app.services.torrent_service.ensure_fresh_tracker_stats", fake_ensure_fresh_tracker_stats)
    monkeypatch.setattr("app.services.torrent_service._get_active_tracker_deltas", fake_get_active_tracker_deltas)
    monkeypatch.setattr("app.services.torrent_service._get_pending_reserved_size", fake_get_pending_reserved_size)
    monkeypatch.setattr("app.services.torrent_service.storage_allowed", fake_storage_allowed)
    monkeypatch.setattr("app.services.torrent_service._tracker_min_ratio", lambda _tracker: 1.6)

    request = ForecastRequest(
        tracker="c411",
        torrent="magnet:?xt=urn:btih:abc",
        min_ratio=0,
        max_storage_bytes=0,
    )

    decision = await forecast_torrent(db=None, request=request)

    assert observed["max_storage_bytes"] is None
    assert decision.minimum_ratio == 1.6
    assert decision.max_storage_bytes == 999


@pytest.mark.asyncio
async def test_forecast_torrent_positive_overrides_are_applied(monkeypatch) -> None:
    async def fake_ensure_fresh_tracker_stats(_db, _tracker):
        return SimpleNamespace(raw_upload=100.0, raw_download=50.0, raw_ratio=2.0)

    async def fake_get_active_tracker_deltas(_tracker):
        return 0.0, 0.0, []

    async def fake_get_pending_reserved_size(_db, _tracker):
        return 0

    observed: dict[str, int | None] = {"max_storage_bytes": None}

    def fake_storage_allowed(*, extra_reserved_bytes: int, max_storage_bytes: int | None):
        assert extra_reserved_bytes == 0
        observed["max_storage_bytes"] = max_storage_bytes
        return True, "Storage allowed", {
            "current_used_bytes": 10,
            "forecast_used_bytes": 10,
            "max_storage_bytes": 999,
        }

    monkeypatch.setattr("app.services.torrent_service.ensure_fresh_tracker_stats", fake_ensure_fresh_tracker_stats)
    monkeypatch.setattr("app.services.torrent_service._get_active_tracker_deltas", fake_get_active_tracker_deltas)
    monkeypatch.setattr("app.services.torrent_service._get_pending_reserved_size", fake_get_pending_reserved_size)
    monkeypatch.setattr("app.services.torrent_service.storage_allowed", fake_storage_allowed)
    monkeypatch.setattr("app.services.torrent_service._tracker_min_ratio", lambda _tracker: 1.6)

    request = ForecastRequest(
        tracker="c411",
        torrent="magnet:?xt=urn:btih:def",
        min_ratio=1.2,
        max_storage_bytes=123456,
    )

    decision = await forecast_torrent(db=None, request=request)

    assert observed["max_storage_bytes"] == 123456
    assert decision.minimum_ratio == 1.2
    assert decision.max_storage_bytes == 123456
