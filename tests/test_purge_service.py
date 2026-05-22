from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.core.time import utcnow
from app.services.purge_service import purge_torrents


@pytest.mark.asyncio
async def test_purge_torrents_dry_run_does_not_remove(monkeypatch) -> None:
    torrent = SimpleNamespace(
        id=1,
        hash_string="hash1",
        name="Torrent 1",
        ratio=3.0,
        added_date=utcnow() - timedelta(hours=50),
        total_size=1000,
        trackers=["https://tracker.c411.org/announce"],
    )

    removed_ids: list[int] = []

    async def fake_list_torrents():
        return [torrent]

    async def fake_remove_torrent(torrent_id: int, delete_data: bool):
        removed_ids.append(torrent_id)

    monkeypatch.setattr("app.services.purge_service.list_torrents", fake_list_torrents)
    monkeypatch.setattr("app.services.purge_service.remove_torrent", fake_remove_torrent)

    result = await purge_torrents(
        tracker="c411",
        target_ratio=2.0,
        max_lifetime_hours=24,
        delete_data=False,
        dry_run=True,
    )

    assert result["matched_count"] == 1
    assert result["total_reclaimable_bytes"] == 1000
    assert "ratio_above_target" in result["torrents"][0]["reasons"]
    assert "lifetime_exceeded" in result["torrents"][0]["reasons"]
    assert removed_ids == []


@pytest.mark.asyncio
async def test_purge_torrents_executes_removal_when_not_dry_run(monkeypatch) -> None:
    torrent = SimpleNamespace(
        id=10,
        hash_string="hash10",
        name="Torrent 10",
        ratio=4.0,
        added_date=utcnow() - timedelta(hours=10),
        total_size=2048,
        trackers=["https://tracker.torr9.net/announce"],
    )

    removed_ids: list[int] = []

    async def fake_list_torrents():
        return [torrent]

    async def fake_remove_torrent(torrent_id: int, delete_data: bool):
        assert delete_data is True
        removed_ids.append(torrent_id)

    monkeypatch.setattr("app.services.purge_service.list_torrents", fake_list_torrents)
    monkeypatch.setattr("app.services.purge_service.remove_torrent", fake_remove_torrent)

    result = await purge_torrents(
        tracker="torr9",
        target_ratio=2.0,
        max_lifetime_hours=None,
        delete_data=True,
        dry_run=False,
    )

    assert result["matched_count"] == 1
    assert removed_ids == [10]
