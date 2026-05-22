import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

load_dotenv()


class Base(DeclarativeBase):
    pass


def _default_database_url() -> str:
    config_dir = Path(os.getenv("CONFIG_DIR", ".config"))
    if not config_dir.is_absolute():
        config_dir = Path(__file__).parent / config_dir
    config_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{config_dir / 'tracker_tools.db'}"


DATABASE_URL = os.getenv("DATABASE_URL", _default_database_url())

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    from tracker_torrent_models import TrackerStatsSnapshot, TrackedTorrent, TorrentReservation

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
