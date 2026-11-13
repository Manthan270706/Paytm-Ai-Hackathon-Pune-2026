import os
from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.seed import reset_and_seed
from app.db.session import AsyncSession, _create_engine, async_sessionmaker, get_db_session
from app.main import app

SHARED_TEST_DB = "sqlite+aiosqlite:///./test_shared.db"
shared_engine = _create_engine(SHARED_TEST_DB, is_verifier=False)
shared_session_factory = async_sessionmaker(
    bind=shared_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with shared_session_factory() as session:
        yield session


app.dependency_overrides[get_db_session] = override_get_db


@pytest.fixture(autouse=True, scope="session")
async def setup_test_suite_db() -> AsyncGenerator[None, None]:
    # Initialize schema and seed frozen scenario once for all tests
    async with shared_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with shared_session_factory() as session:
        await reset_and_seed(session)

    yield

    async with shared_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await shared_engine.dispose()
    if os.path.exists("./test_shared.db"):
        try:
            os.remove("./test_shared.db")
        except OSError:
            pass


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app)
