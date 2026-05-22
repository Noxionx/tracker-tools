from app.schemas.torrent import AddTorrentRequest, ForecastRequest


def test_forecast_request_accepts_tracker_and_torrent_only() -> None:
    payload = ForecastRequest(tracker="torr9", torrent="magnet:?xt=urn:btih:abc")

    assert payload.tracker == "torr9"
    assert payload.torrent.startswith("magnet:")
    assert payload.is_freeleech is False
    assert payload.min_ratio is None
    assert payload.max_storage_bytes is None


def test_add_request_accepts_tracker_and_torrent_only() -> None:
    payload = AddTorrentRequest(tracker="c411", torrent="magnet:?xt=urn:btih:def")

    assert payload.tracker == "c411"
    assert payload.torrent.startswith("magnet:")
    assert payload.is_freeleech is False
    assert payload.min_ratio is None
    assert payload.max_storage_bytes is None


def test_forecast_request_accepts_freeleech_override() -> None:
    payload = ForecastRequest(
        tracker="c411",
        torrent="magnet:?xt=urn:btih:ghi",
        is_freeleech=True,
    )

    assert payload.is_freeleech is True
