import os
from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.seed import reset_and_seed
from app.db.session import (
    AsyncSession,
    _create_engine,
    async_sessionmaker,
    get_db_session,
    get_verifier_db,
)
from app.main import app

SHARED_TEST_DB = "sqlite+aiosqlite:///./test_shared.db"
shared_engine = _create_engine(SHARED_TEST_DB, is_verifier=False)
shared_session_factory = async_sessionmaker(
    bind=shared_engine, class_=AsyncSession, expire_on_commit=False
)
shared_verifier_engine = _create_engine(SHARED_TEST_DB, is_verifier=True)
shared_verifier_session_factory = async_sessionmaker(
    bind=shared_verifier_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with shared_session_factory() as session:
        yield session


async def override_get_verifier_db() -> AsyncGenerator[AsyncSession, None]:
    async with shared_verifier_session_factory() as session:
        yield session


app.dependency_overrides[get_db_session] = override_get_db
app.dependency_overrides[get_verifier_db] = override_get_verifier_db


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
    await shared_verifier_engine.dispose()
    if os.path.exists("./test_shared.db"):
        try:
            os.remove("./test_shared.db")
        except OSError:
            pass


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app)


def generate_test_paytm_checksum(
    params: dict[str, object], key: str = "0123456789abcdef", salt: str = "aB3x"
) -> str:
    """Helper generating standard Paytm AES-CBC PKCS7 encrypted checksum for test payloads."""
    import base64
    import hashlib

    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    iv = b"@@@@&&&&####$$$$"
    parameter_string = "|".join(str(params[k]) for k in sorted(params))
    digest = hashlib.sha256(f"{parameter_string}|{salt}".encode()).hexdigest() + salt
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded = padder.update(digest.encode("ascii")) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key.encode("utf-8")), modes.CBC(iv)).encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(ciphertext).decode("ascii")
