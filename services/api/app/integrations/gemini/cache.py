import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LLMCache
from app.integrations.gemini.fixtures import (
    GOLDEN_EXTRACTION_FIXTURE,
    GOLDEN_INTENT_FIXTURE,
    compute_request_hash,
    matches_golden_scenario,
)

logger = logging.getLogger(__name__)

# Process-level in-memory cache for fast replay
_MEMORY_CACHE: dict[str, dict[str, Any]] = {}


async def get_cached_llm_response(
    prompt: str,
    schema_name: str,
    system_prompt: str | None = None,
    session: AsyncSession | None = None,
) -> dict[str, Any] | None:
    """Retrieve pre-recorded or dynamically cached LLM structured response."""
    req_hash = compute_request_hash(prompt, schema_name, system_prompt)

    # 1. In-memory hash lookup
    if req_hash in _MEMORY_CACHE:
        return _MEMORY_CACHE[req_hash]

    # 2. Database lookup in llm_cache table
    if session is not None:
        try:
            stmt = select(LLMCache).where(LLMCache.request_hash == req_hash)
            row = (await session.execute(stmt)).scalars().first()
            if row and row.response_json:
                _MEMORY_CACHE[req_hash] = row.response_json
                return row.response_json
        except Exception as e:
            logger.debug(f"DB cache read error (falling back to memory): {e}")

    # 3. Golden scenario pre-recorded fixtures (PRD §12.3)
    if matches_golden_scenario(prompt):
        if schema_name == "EntityExtractionResult":
            return dict(GOLDEN_EXTRACTION_FIXTURE)
        if schema_name == "IntentClassificationResult":
            return dict(GOLDEN_INTENT_FIXTURE)

    return None


async def store_cached_llm_response(
    prompt: str,
    schema_name: str,
    response_json: dict[str, Any],
    system_prompt: str | None = None,
    session: AsyncSession | None = None,
) -> None:
    """Persist structured LLM response to memory and durable database table."""
    req_hash = compute_request_hash(prompt, schema_name, system_prompt)
    _MEMORY_CACHE[req_hash] = response_json

    if session is not None:
        try:
            stmt = select(LLMCache).where(LLMCache.key_hash == req_hash)
            existing = (await session.execute(stmt)).scalars().first()
            if not existing:
                cached_row = LLMCache(
                    key_hash=req_hash,
                    request_hash=req_hash,
                    response_json=response_json,
                )
                session.add(cached_row)
                await session.flush()
        except Exception as e:
            logger.debug(f"DB cache write skipped: {e}")
