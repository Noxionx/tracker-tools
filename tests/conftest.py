from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import dependencies
from app.db.base import Base
from app.main import create_app
from app.models import tracker as _tracker_models  # noqa: F401


@pytest_asyncio.fixture
async def db_session_factory(tmp_path) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    database_path = tmp_path / "integration_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}", echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield session_factory
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def test_app(db_session_factory: async_sessionmaker[AsyncSession]):
    app = create_app()

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[dependencies.get_db_session] = override_get_db_session
    return app


@pytest_asyncio.fixture
async def api_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
