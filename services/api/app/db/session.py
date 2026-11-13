import asyncio
import sys
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass


def _create_engine(url: str, is_verifier: bool = False) -> AsyncEngine:
    connect_args: dict = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    elif "psycopg" in url:
        connect_args["connect_timeout"] = 2

    engine = create_async_engine(
        url,
        echo=False,
        future=True,
        connect_args=connect_args,
    )

    if url.startswith("sqlite"):

        @event.listens_for(engine.sync_engine, "connect")
        def _configure_sqlite(dbapi_connection: object, connection_record: object) -> None:
            cursor = getattr(dbapi_connection, "cursor", lambda: None)()
            if cursor:
                cursor.execute("PRAGMA foreign_keys=ON")
                if is_verifier:
                    cursor.execute("PRAGMA query_only=ON")
                cursor.close()

    return engine


engine: AsyncEngine = _create_engine(settings.DATABASE_URL, is_verifier=False)
verifier_engine: AsyncEngine = _create_engine(settings.VERIFIER_DATABASE_URL, is_verifier=True)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

verifier_session_factory = async_sessionmaker(
    bind=verifier_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_verifier_db() -> AsyncGenerator[AsyncSession, None]:
    async with verifier_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


get_db_session = get_db
