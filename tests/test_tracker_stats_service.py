from app.services.tracker_stats_service import compute_ratio


def test_compute_ratio_with_download() -> None:
    assert compute_ratio(50.0, 10.0) == 5.0


def test_compute_ratio_with_upload_only() -> None:
    assert compute_ratio(10.0, 0.0) == 999.0


def test_compute_ratio_with_zero_values() -> None:
    assert compute_ratio(0.0, 0.0) == 0.0
