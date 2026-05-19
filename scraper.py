import logging
from typing import Dict, Any
from dotenv import load_dotenv

from util import UnknownTrackerError, ScrappingError, list_scrappers, load_scrapper

load_dotenv()
logger = logging.getLogger("scraper")


async def get_stats(site: str, headless: bool = True) -> Dict[str, Any]:
    """Scrapes the site and returns a dictionary of stats (ratio, upload, download)"""
    try:
        if site in list_scrappers():
            scrapper = load_scrapper(site)
            return await scrapper.get_stats(headless)
        else:
            raise UnknownTrackerError(f"Unknown tracker {site}")
    except Exception as e:
        logger.error(f"Error {site}: {e}")
        raise ScrappingError(e)
