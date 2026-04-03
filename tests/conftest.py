import os
from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///./test.db")
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")


@pytest_asyncio.fixture
async def app(tmp_path) -> AsyncIterator:
    db_path = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["DATABASE_URL_SYNC"] = f"sqlite:///{db_path}"

    from core.config import get_settings

    get_settings.cache_clear()

    from infrastructure.db import session as session_module
    from infrastructure.db.base import Base

    test_engine = create_async_engine(os.environ["DATABASE_URL"], future=True)
    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    session_module.engine = test_engine
    session_module.SessionFactory = test_session_factory

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from main import app as fastapi_app

    yield fastapi_app

    await test_engine.dispose()


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client
