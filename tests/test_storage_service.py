from app.services.storage_service import storage_allowed


def test_storage_allowed_when_within_limits(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.storage_service.get_storage_status",
        lambda extra_reserved_bytes=0: {
            "current_used_bytes": 100,
            "forecast_used_bytes": 200,
            "max_storage_bytes": 500,
            "disk_total_bytes": 1000,
            "disk_used_bytes": 500,
            "disk_free_bytes": 500,
            "min_free_storage_bytes": 100,
            "configured": True,
            "download_dir": "/tmp",
        },
    )

    allowed, reason, _ = storage_allowed(extra_reserved_bytes=100)
    assert allowed
    assert reason == "Storage allowed"


def test_storage_blocked_when_forecast_exceeds_max(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.storage_service.get_storage_status",
        lambda extra_reserved_bytes=0: {
            "current_used_bytes": 100,
            "forecast_used_bytes": 900,
            "max_storage_bytes": 500,
            "disk_total_bytes": 1000,
            "disk_used_bytes": 500,
            "disk_free_bytes": 500,
            "min_free_storage_bytes": 100,
            "configured": True,
            "download_dir": "/tmp",
        },
    )

    allowed, reason, _ = storage_allowed(extra_reserved_bytes=100)
    assert not allowed
    assert reason == "Forecast storage usage would exceed maximum allowed storage"
