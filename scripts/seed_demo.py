#!/usr/bin/env python3
"""scripts/seed_demo.py: CLI command to reset and seed the database to the frozen demo state."""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

# Add services/api to sys.path so app imports work
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "services" / "api"))

from app.db.base import Base  # noqa: E402
from app.db.seed import reset_and_seed  # noqa: E402
from app.db.session import (  # noqa: E402
    AsyncSession,
    _create_engine,
    async_sessionmaker,
    engine,
    get_db_session,
)


async def main() -> None:
    active_engine = engine
    active_session_factory = None

    use_sqlite = "--sqlite" in sys.argv or "--local" in sys.argv
    if use_sqlite:
        sqlite_url = "sqlite+aiosqlite:///./opssaathi_demo.db"
        print(f"Using local SQLite database ({sqlite_url})...")
        active_engine = _create_engine(sqlite_url, is_verifier=False)
        active_session_factory = async_sessionmaker(
            bind=active_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with active_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    else:
        try:
            print("Connecting to primary database...")
            async with active_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            print(f"PostgreSQL connection failed ({e}). Falling back to local SQLite database...")
            sqlite_url = "sqlite+aiosqlite:///./opssaathi_demo.db"
            active_engine = _create_engine(sqlite_url, is_verifier=False)
            active_session_factory = async_sessionmaker(
                bind=active_engine, class_=AsyncSession, expire_on_commit=False
            )
            async with active_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

    print("Executing reset_and_seed...")
    if active_session_factory:
        async with active_session_factory() as session:
            result = await reset_and_seed(session)
    else:
        async for session in get_db_session():
            result = await reset_and_seed(session)
            break

    print("=" * 60)
    print("Demo Database Seeded Successfully (Frozen Golden Scenario):")
    print("=" * 60)
    print(f"  Merchant ID:     {result['merchant_id']}")
    print(f"  Batch Ref:       {result['batch_ref']}")
    print(f"  Expected Net:    Rs {Decimal(str(result['expected_net'])):,.2f}")
    print(f"  Observed Net:    Rs {Decimal(str(result['observed_net'])):,.2f}")
    print(
        f"  Discrepancy:     Rs {Decimal(str(result['discrepancy'])):,.2f} "
        f"({result['reason_code']})"
    )
    print(f"  Missing Txn Ref: {result['missing_txn_id']} ({result['missing_order_id']})")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
