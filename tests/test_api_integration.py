from __future__ import annotations

from datetime import timedelta

import pytest
from app.models.tracker import TrackerStatsSnapshot
from app.schemas.torrent import DecisionResponse
from app.services.tracker_stats_service import serialize_tracker_stats
from app.core.time import utcnow


@pytest.mark.asyncio
async def test_root_endpoint_lists_admit(api_client) -> None:
    response = await api_client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert "/torrents/admit" in payload["endpoints"]
    assert "/torrents/check-and-add" not in payload["endpoints"]


@pytest.mark.asyncio
async def test_trackers_endpoint_returns_registry(api_client, monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.system.list_scrapers", lambda: ["c411", "torr9"])

    response = await api_client.get("/trackers")

    assert response.status_code == 200
    assert response.json() == {"trackers": ["c411", "torr9"]}


@pytest.mark.asyncio
async def test_tracker_stats_and_history_endpoints(api_client, db_session_factory) -> None:
    now = utcnow()
    snapshot = TrackerStatsSnapshot(
        tracker_name="c411",
        raw_upload=200.0,
        raw_download=100.0,
        raw_ratio=2.0,
        bonus=0.0,
        scraped_at=now,
        changed_at=now,
        error=None,
    )

    async with db_session_factory() as session:
        session.add(snapshot)
        await session.commit()

    stats_response = await api_client.get("/trackers/c411/stats")
    history_response = await api_client.get("/trackers/c411/history")

    assert stats_response.status_code == 200
    assert history_response.status_code == 200
    assert stats_response.json()["tracker"] == "c411"
    assert history_response.json()["tracker"] == "c411"
    assert len(history_response.json()["items"]) == 1


@pytest.mark.asyncio
async def test_tracker_stats_returns_404_when_missing(api_client) -> None:
    response = await api_client.get("/trackers/unknown/stats")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_forecast_accepts_minimal_payload(api_client, monkeypatch) -> None:
    async def fake_forecast(_db, request):
        assert request.tracker == "c411"
        assert request.torrent.startswith("magnet:")
        assert request.min_ratio is None
        assert request.max_storage_bytes is None
        return DecisionResponse(
            allowed=True,
            added=False,
            reason="ok",
            tracker=request.tracker,
            current_ratio=2.0,
            forecast_ratio=1.8,
            minimum_ratio=1.0,
            current_upload=100.0,
            current_download=50.0,
            forecast_upload=100.0,
            forecast_download=55.0,
            current_storage_bytes=10,
            forecast_storage_bytes=20,
            max_storage_bytes=0,
        )

    monkeypatch.setattr("app.api.routes.torrents.forecast_torrent", fake_forecast)

    response = await api_client.post(
        "/torrents/forecast",
        json={"tracker": "c411", "torrent": "magnet:?xt=urn:btih:abc"},
    )

    assert response.status_code == 200
    assert response.json()["allowed"] is True


@pytest.mark.asyncio
async def test_forecast_requires_torrent_field(api_client) -> None:
    response = await api_client.post(
        "/torrents/forecast",
        json={"tracker": "c411"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_admit_accepts_minimal_payload(api_client, monkeypatch) -> None:
    async def fake_admit(_db, request):
        assert request.tracker == "torr9"
        assert request.torrent.startswith("magnet:")
        assert request.min_ratio is None
        assert request.max_storage_bytes is None
        return DecisionResponse(
            allowed=True,
            added=True,
            reason="admitted",
            tracker=request.tracker,
            current_ratio=2.0,
            forecast_ratio=1.9,
            minimum_ratio=1.0,
            current_upload=100.0,
            current_download=50.0,
            forecast_upload=100.0,
            forecast_download=53.0,
            current_storage_bytes=10,
            forecast_storage_bytes=20,
            max_storage_bytes=0,
            torrent_hash="abc",
            torrent_name="test",
            torrent_size_bytes=123,
        )

    monkeypatch.setattr("app.api.routes.torrents.admit_torrent", fake_admit)

    response = await api_client.post(
        "/torrents/admit",
        json={"tracker": "torr9", "torrent": "magnet:?xt=urn:btih:def"},
    )

    assert response.status_code == 200
    assert response.json()["added"] is True


@pytest.mark.asyncio
async def test_admit_requires_torrent_field(api_client) -> None:
    response = await api_client.post(
        "/torrents/admit",
        json={"tracker": "torr9"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_purge_requires_at_least_one_condition(api_client) -> None:
    response = await api_client.post("/torrents/purge", json={"dry_run": True})

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_storage_endpoint(api_client, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.storage.get_storage_status",
        lambda: {
            "download_dir": "/data",
            "current_used_bytes": 100,
            "forecast_used_bytes": 100,
            "max_storage_bytes": 0,
            "disk_total_bytes": 1000,
            "disk_used_bytes": 300,
            "disk_free_bytes": 700,
            "min_free_storage_bytes": 0,
            "configured": True,
        },
    )

    response = await api_client.get("/storage")

    assert response.status_code == 200
    assert response.json()["configured"] is True


@pytest.mark.asyncio
async def test_debug_latest_snapshots_endpoint(api_client, db_session_factory) -> None:
    now = utcnow()
    older = now - timedelta(minutes=1)

    first = TrackerStatsSnapshot(
        tracker_name="c411",
        raw_upload=120.0,
        raw_download=60.0,
        raw_ratio=2.0,
        bonus=0.0,
        scraped_at=older,
        changed_at=older,
        error=None,
    )
    second = TrackerStatsSnapshot(
        tracker_name="c411",
        raw_upload=140.0,
        raw_download=70.0,
        raw_ratio=2.0,
        bonus=0.0,
        scraped_at=now,
        changed_at=now,
        error=None,
    )

    async with db_session_factory() as session:
        session.add(first)
        session.add(second)
        await session.commit()

    response = await api_client.get("/debug/latest-snapshots")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 2
    expected_top = serialize_tracker_stats(second)
    assert payload["items"][0]["tracker"] == expected_top["tracker"]
    assert payload["items"][0]["upload"] == expected_top["upload"]
