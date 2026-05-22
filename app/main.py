from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import debug, storage, system, torrents, trackers
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import init_db
from app.services.scheduler_service import build_scheduler, refresh_all_trackers_job

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize resources and start background jobs."""

    await init_db()
    asyncio.create_task(refresh_all_trackers_job())

    scheduler = build_scheduler(settings.refresh_interval_minutes)
    scheduler.start()

    try:
        yield
    finally:
        scheduler.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.include_router(system.router)
    app.include_router(trackers.router)
    app.include_router(torrents.router)
    app.include_router(storage.router)
    app.include_router(debug.router)

    return app


app = create_app()
