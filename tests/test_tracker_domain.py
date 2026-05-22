from app.services.tracker_domain import announce_matches_tracker, torrent_belongs_to_tracker


def test_announce_matches_tracker_domain() -> None:
    assert announce_matches_tracker("https://tracker.c411.org/announce", "c411")


def test_announce_does_not_match_tracker_domain() -> None:
    assert not announce_matches_tracker("https://example.com/announce", "c411")


def test_torrent_belongs_to_tracker() -> None:
    urls = [
        "https://tracker.example.com/announce",
        "https://subdomain.torr9.net/announce",
    ]
    assert torrent_belongs_to_tracker(urls, "torr9")
