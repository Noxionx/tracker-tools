import asyncio
import os
import logging
from datetime import datetime
from typing import Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from scraper import get_stats
from util import list_scrappers

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

ratios_cache: Dict[str, Any] = {}


async def update_all():
    global ratios_cache
    for site in list_scrappers():
        try:
            logger.info(f"updating stats for tracker : {site}")
            stats = await get_stats(site)
            raw_ratio = stats["raw_upload"] / stats["raw_download"] if stats["raw_download"] > 0 else 999 if stats["raw_upload"] > 0 else 0
            ratios_cache[site] = {**stats, "raw_ratio": raw_ratio, "last_updated": datetime.now().isoformat()}
        except Exception as e:
            logger.error(f"Error while scrapping {site}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(update_all())
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        update_all, "interval", minutes=int(os.getenv("REFRESH_INTERVAL_MINUTES", 60))
    )
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

def format_cache():
    return {
        site: {
            "ratio": ratios_cache[site]["raw_ratio"],
            "upload": ratios_cache[site]["raw_upload"],
            "download": ratios_cache[site]["raw_download"],
            "bonus": ratios_cache[site].get("bonus", 0),
        } for site in ratios_cache
    }

@app.get("/")
async def root():
    return {"message": "Scrap Ratio API is running", "endpoints": ["/ratios"]}


@app.get("/ratios")
async def get_ratios():
    return format_cache()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8679)
