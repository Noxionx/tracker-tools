from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from importlib import import_module, reload


def _load_transmission_service_with_stub():
    # Ensure the service module can be imported in tests even if transmission-rpc
    # is not installed in the test environment.
    fake_module = types.ModuleType("transmission_rpc")

    class FakeClient:
        pass

    fake_module.Client = FakeClient
    sys.modules["transmission_rpc"] = fake_module
    module = import_module("app.services.transmission_service")
    return reload(module)


def test_to_info_normalizes_naive_datetimes_to_utc_aware() -> None:
    service = _load_transmission_service_with_stub()

    class FakeTorrent:
        id = 7
        hash_string = "abc"
        name = "torrent"
        total_size = 100
        downloaded_ever = 10
        uploaded_ever = 20
        ratio = 2.0
        status = "seeding"
        added_date = datetime(2026, 5, 22, 10, 0, 0)
        done_date = datetime(2026, 5, 22, 11, 0, 0)
        download_dir = "/downloads"
        tracker_stats = []
        trackers = []

    info = service._to_info(FakeTorrent())

    assert info.added_date is not None
    assert info.done_date is not None
    assert info.added_date.tzinfo is not None
    assert info.done_date.tzinfo is not None
    assert info.added_date.utcoffset() == timezone.utc.utcoffset(None)
    assert info.done_date.utcoffset() == timezone.utc.utcoffset(None)


def test_to_info_converts_aware_datetimes_to_utc() -> None:
    service = _load_transmission_service_with_stub()

    class FakeTorrent:
        id = 8
        hash_string = "def"
        name = "torrent-aware"
        total_size = 200
        downloaded_ever = 15
        uploaded_ever = 30
        ratio = 2.0
        status = "seeding"
        added_date = datetime(2026, 5, 22, 12, 0, 0, tzinfo=timezone.utc)
        done_date = datetime(2026, 5, 22, 13, 0, 0, tzinfo=timezone.utc)
        download_dir = "/downloads"
        tracker_stats = []
        trackers = []

    info = service._to_info(FakeTorrent())

    assert info.added_date is not None
    assert info.done_date is not None
    assert info.added_date.tzinfo is not None
    assert info.done_date.tzinfo is not None
    assert info.added_date.utcoffset() == timezone.utc.utcoffset(None)
    assert info.done_date.utcoffset() == timezone.utc.utcoffset(None)


def test_to_info_keeps_none_datetime_fields() -> None:
    service = _load_transmission_service_with_stub()

    class FakeTorrent:
        id = 9
        hash_string = "ghi"
        name = "torrent-none"
        total_size = 300
        downloaded_ever = 0
        uploaded_ever = 0
        ratio = 0.0
        status = "stopped"
        added_date = None
        done_date = None
        download_dir = "/downloads"
        tracker_stats = []
        trackers = []

    info = service._to_info(FakeTorrent())

    assert info.added_date is None
    assert info.done_date is None
