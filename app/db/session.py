from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.base import Base

settings = get_settings()


def _prepare_database_url(raw_url: str) -> str:
    """Normalize SQLite file URLs and create parent directories eagerly."""

    sqlite_prefix = "sqlite+aiosqlite:///"
    if not raw_url.startswith(sqlite_prefix):
        return raw_url

    location = raw_url[len(sqlite_prefix) :]
    if location in {":memory:", ""} or location.startswith("file:"):
        return raw_url

    db_path = Path(location).expanduser()
    if not db_path.is_absolute():
        db_path = (Path.cwd() / db_path).resolve()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"{sqlite_prefix}{db_path}"


DATABASE_URL = _prepare_database_url(settings.resolved_database_url)
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """Create tables if they do not already exist."""

    from app.models import tracker as _tracker_models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency returning an async SQLAlchemy session."""

    async with SessionLocal() as session:
        yield session
