from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.time import utcnow
from app.models.tracker import TorrentReservation, TrackedTorrent
from app.schemas.torrent import AddTorrentRequest, DecisionResponse, ForecastRequest
from app.services.torrent_service import (
    _get_tracker_active_download_commitment,
    admit_torrent,
    build_forecast_breakdown,
    forecast_torrent,
)


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

    async def fake_add_torrent(*, torrent: str, download_dir: str | None, paused: bool, labels: list[str] | None):
        assert torrent.startswith("magnet:")
        assert download_dir == "/tmp"
        assert paused is False
        assert labels == ["c411"]
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

    async def fake_add_torrent(*, torrent: str, download_dir: str | None, paused: bool, labels: list[str] | None):
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

    async def fake_get_tracker_active_download_commitment(_tracker, _scraped_at):
        return 0.0, []

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
    monkeypatch.setattr(
        "app.services.torrent_service._get_tracker_active_download_commitment",
        fake_get_tracker_active_download_commitment,
    )
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

    async def fake_get_tracker_active_download_commitment(_tracker, _scraped_at):
        return 0.0, []

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
    monkeypatch.setattr(
        "app.services.torrent_service._get_tracker_active_download_commitment",
        fake_get_tracker_active_download_commitment,
    )
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


@pytest.mark.asyncio
async def test_forecast_torrent_freeleech_impacts_storage_not_ratio(monkeypatch) -> None:
    async def fake_ensure_fresh_tracker_stats(_db, _tracker):
        return SimpleNamespace(raw_upload=100.0, raw_download=100.0, raw_ratio=1.0)

    async def fake_get_tracker_active_download_commitment(_tracker, _scraped_at):
        return 0.0, []

    async def fake_get_pending_reserved_size(_db, _tracker):
        return 0

    observed_extra_reserved: list[int] = []

    def fake_storage_allowed(*, extra_reserved_bytes: int, max_storage_bytes: int | None):
        observed_extra_reserved.append(extra_reserved_bytes)
        assert max_storage_bytes is None
        return True, "Storage allowed", {
            "current_used_bytes": 10,
            "forecast_used_bytes": 10 + extra_reserved_bytes,
            "max_storage_bytes": 1000,
        }

    monkeypatch.setattr("app.services.torrent_service.ensure_fresh_tracker_stats", fake_ensure_fresh_tracker_stats)
    monkeypatch.setattr(
        "app.services.torrent_service._get_tracker_active_download_commitment",
        fake_get_tracker_active_download_commitment,
    )
    monkeypatch.setattr("app.services.torrent_service._get_pending_reserved_size", fake_get_pending_reserved_size)
    monkeypatch.setattr("app.services.torrent_service.storage_allowed", fake_storage_allowed)
    monkeypatch.setattr("app.services.torrent_service._tracker_min_ratio", lambda _tracker: 0.8)

    normal_request = ForecastRequest(
        tracker="c411",
        torrent="magnet:?xt=urn:btih:normal",
        size_bytes=50,
        is_freeleech=False,
    )
    freeleech_request = ForecastRequest(
        tracker="c411",
        torrent="magnet:?xt=urn:btih:free",
        size_bytes=50,
        is_freeleech=True,
    )

    normal_decision = await forecast_torrent(db=None, request=normal_request)
    freeleech_decision = await forecast_torrent(db=None, request=freeleech_request)

    assert observed_extra_reserved == [50, 50]
    assert normal_decision.forecast_download == 150.0
    assert normal_decision.allowed is False
    assert freeleech_decision.forecast_download == 150.0
    assert freeleech_decision.allowed is False


@pytest.mark.asyncio
async def test_forecast_torrent_silverleech_ratio(monkeypatch) -> None:
    async def fake_ensure_fresh_tracker_stats(_db, _tracker):
        return SimpleNamespace(raw_upload=100.0, raw_download=100.0, raw_ratio=1.0)

    async def fake_get_tracker_active_download_commitment(_tracker, _scraped_at):
        return 0.0, []

    async def fake_get_pending_reserved_size(_db, _tracker):
        return 0

    def fake_storage_allowed(*, extra_reserved_bytes: int, max_storage_bytes: int | None):
        return True, "Storage allowed", {
            "current_used_bytes": 10,
            "forecast_used_bytes": 10 + extra_reserved_bytes,
            "max_storage_bytes": 1000,
        }

    monkeypatch.setattr("app.services.torrent_service.ensure_fresh_tracker_stats", fake_ensure_fresh_tracker_stats)
    monkeypatch.setattr(
        "app.services.torrent_service._get_tracker_active_download_commitment",
        fake_get_tracker_active_download_commitment,
    )
    monkeypatch.setattr("app.services.torrent_service._get_pending_reserved_size", fake_get_pending_reserved_size)
    monkeypatch.setattr("app.services.torrent_service.storage_allowed", fake_storage_allowed)
    monkeypatch.setattr("app.services.torrent_service._tracker_min_ratio", lambda _tracker: 0.8)

    request = ForecastRequest(
        tracker="c411",
        torrent="magnet:?xt=urn:btih:silver",
        size_bytes=50,
        freeleech_ratio=0.5,
    )

    decision = await forecast_torrent(db=None, request=request)

    assert decision.forecast_download == 150.0


@pytest.mark.asyncio
async def test_forecast_torrent_anchors_on_tracker_for_completed_untracked(monkeypatch) -> None:
    async def fake_ensure_fresh_tracker_stats(_db, _tracker):
        return SimpleNamespace(raw_upload=200.0, raw_download=100.0, raw_ratio=2.0)

    async def fake_get_tracker_active_download_commitment(_tracker, _scraped_at):
        # Completed untracked torrents should not force permanent cumulative deltas.
        return 0.0, []

    async def fake_get_pending_reserved_size(_db, _tracker):
        return 0

    def fake_storage_allowed(*, extra_reserved_bytes: int, max_storage_bytes: int | None):
        return True, "Storage allowed", {
            "current_used_bytes": 10,
            "forecast_used_bytes": 10 + extra_reserved_bytes,
            "max_storage_bytes": 1000,
        }

    monkeypatch.setattr("app.services.torrent_service.ensure_fresh_tracker_stats", fake_ensure_fresh_tracker_stats)
    monkeypatch.setattr(
        "app.services.torrent_service._get_tracker_active_download_commitment",
        fake_get_tracker_active_download_commitment,
    )
    monkeypatch.setattr("app.services.torrent_service._get_pending_reserved_size", fake_get_pending_reserved_size)
    monkeypatch.setattr("app.services.torrent_service.storage_allowed", fake_storage_allowed)
    monkeypatch.setattr("app.services.torrent_service._tracker_min_ratio", lambda _tracker: 1.5)

    request = ForecastRequest(
        tracker="c411",
        torrent="magnet:?xt=urn:btih:anchor",
        size_bytes=0,
    )

    decision = await forecast_torrent(db=None, request=request)

    assert decision.current_ratio == 2.0
    assert decision.forecast_ratio == 2.0


@pytest.mark.asyncio
async def test_active_download_commitment_excludes_completed_before_snapshot(monkeypatch) -> None:
    snapshot = utcnow()

    completed_before = SimpleNamespace(
        id=1,
        hash_string="done-before",
        name="Done Before",
        total_size=100,
        downloaded_ever=100.0,
        uploaded_ever=50.0,
        ratio=0.5,
        status="seeding",
        done_date=snapshot - timedelta(minutes=10),
        trackers=["https://tracker.c411.org/announce"],
    )
    in_progress = SimpleNamespace(
        id=2,
        hash_string="in-progress",
        name="In Progress",
        total_size=200,
        downloaded_ever=50.0,
        uploaded_ever=0.0,
        ratio=0.0,
        status="downloading",
        done_date=None,
        trackers=["https://tracker.c411.org/announce"],
    )

    async def fake_list_torrents():
        return [completed_before, in_progress]

    monkeypatch.setattr("app.services.torrent_service.list_torrents", fake_list_torrents)

    commitment, matched = await _get_tracker_active_download_commitment("c411", snapshot)

    assert commitment == 200.0
    assert len(matched) == 2
    assert matched[0]["completed_before_snapshot"] is True
    assert matched[0]["counted_download_bytes"] == 0.0
    assert matched[1]["completed_before_snapshot"] is False
    assert matched[1]["counted_download_bytes"] == 200.0


@pytest.mark.asyncio
async def test_forecast_breakdown_confidence_low_with_many_in_progress(monkeypatch) -> None:
    snapshot = utcnow()

    async def fake_ensure_fresh_tracker_stats(_db, _tracker):
        return SimpleNamespace(
            raw_upload=1000.0,
            raw_download=500.0,
            raw_ratio=2.0,
            scraped_at=snapshot,
        )

    async def fake_get_pending_reserved_size(_db, _tracker):
        return 0

    in_progress_a = SimpleNamespace(
        id=1,
        hash_string="ip-a",
        name="IP A",
        total_size=500,
        downloaded_ever=100.0,
        uploaded_ever=10.0,
        ratio=0.1,
        status="downloading",
        done_date=None,
        trackers=["https://tracker.c411.org/announce"],
    )
    in_progress_b = SimpleNamespace(
        id=2,
        hash_string="ip-b",
        name="IP B",
        total_size=700,
        downloaded_ever=50.0,
        uploaded_ever=5.0,
        ratio=0.1,
        status="downloading",
        done_date=None,
        trackers=["https://tracker.c411.org/announce"],
    )

    async def fake_list_torrents():
        return [in_progress_a, in_progress_b]

    monkeypatch.setattr("app.services.torrent_service.ensure_fresh_tracker_stats", fake_ensure_fresh_tracker_stats)
    monkeypatch.setattr("app.services.torrent_service._get_pending_reserved_size", fake_get_pending_reserved_size)
    monkeypatch.setattr("app.services.torrent_service.list_torrents", fake_list_torrents)

    breakdown = await build_forecast_breakdown(
        db=None,
        request=ForecastRequest(
            tracker="c411",
            torrent="magnet:?xt=urn:btih:conf",
            size_bytes=100,
        ),
    )

    assert breakdown["active_download_commitment"] == 1200.0
    assert breakdown["confidence_level"] == "low"
    assert breakdown["confidence_score"] <= 0.1
    assert breakdown["confidence_inputs"]["in_progress_count"] == 2
