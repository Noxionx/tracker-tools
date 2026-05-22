import os
from urllib.parse import urlparse


def _env_domains_for_tracker(tracker: str) -> list[str]:
    key = f"{tracker.upper().replace('-', '_')}_DOMAINS"
    value = os.getenv(key, "")
    return [item.strip().lower() for item in value.split(",") if item.strip()]


DEFAULT_TRACKER_DOMAINS: dict[str, list[str]] = {
    "c411": ["c411.org"],
    "torr9": ["torr9.net", "torr9.to"],
}


def get_tracker_domains(tracker: str) -> list[str]:
    return _env_domains_for_tracker(tracker) or DEFAULT_TRACKER_DOMAINS.get(tracker, [tracker])


def announce_matches_tracker(announce_url: str, tracker: str) -> bool:
    parsed = urlparse(announce_url)
    host = parsed.hostname or announce_url
    host = host.lower()

    for domain in get_tracker_domains(tracker):
        if host == domain or host.endswith(f".{domain}"):
            return True

    return False


def torrent_belongs_to_tracker(announce_urls: list[str], tracker: str) -> bool:
    return any(announce_matches_tracker(url, tracker) for url in announce_urls)
