class UnknownTrackerError(Exception):
    """Raised when a tracker name does not map to a known scraper."""


class ScrapingError(Exception):
    """Raised when a tracker scraper fails."""


class MissingCredentialsError(Exception):
    """Raised when required credentials are missing from environment."""
