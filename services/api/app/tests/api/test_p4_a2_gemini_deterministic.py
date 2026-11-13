import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.integrations import get_llm_provider
from app.integrations.gemini.cache import (
    get_cached_llm_response,
    store_cached_llm_response,
)
from app.integrations.gemini.schemas import (
    EntityExtractionResult,
    IntentClassificationResult,
)
from app.main import app
from app.tests.conftest import shared_session_factory


@pytest.mark.asyncio
async def test_deterministic_llm_cache_direct() -> None:
    """FallbackLLMProvider serves cached structured outputs and flags replay mode."""
    llm = get_llm_provider()
    # Force deterministic replay mode with no API key
    original_deterministic = settings.DEMO_DETERMINISTIC
    original_key = settings.GEMINI_API_KEY
    try:
        settings.DEMO_DETERMINISTIC = True
        settings.GEMINI_API_KEY = None

        prompt = "My ₹6,000 payment from yesterday is missing from settlement"
        res: EntityExtractionResult = await llm.generate_structured(
            prompt=prompt,
            schema=EntityExtractionResult,
        )
        assert res.amount == "6000.00"
        assert res.reference == "BATCH_20261112_01"
        assert getattr(llm, "last_was_replay", False) is True
        assert getattr(llm, "last_served_from", "") == "CACHE"

        intent_res: IntentClassificationResult = await llm.generate_structured(
            prompt=prompt,
            schema=IntentClassificationResult,
        )
        assert intent_res.intent == "SETTLEMENT_MISMATCH"
        assert getattr(llm, "last_was_replay", False) is True
    finally:
        settings.DEMO_DETERMINISTIC = original_deterministic
        settings.GEMINI_API_KEY = original_key


@pytest.mark.asyncio
async def test_database_llm_cache_persistence() -> None:
    """LLMCache correctly persists and reads dynamic request/response pairs from the database."""
    prompt = "Unique test complaint about missing payout"
    schema_name = "EntityExtractionResult"
    test_payload = {
        "amount": "2500.00",
        "reference": "ORDER-9999",
        "category": "PAYOUT_DELAY",
        "missing_fields": [],
    }

    async with shared_session_factory() as session:
        # Store in DB cache
        await store_cached_llm_response(
            prompt=prompt,
            schema_name=schema_name,
            response_json=test_payload,
            session=session,
        )
        await session.commit()

    async with shared_session_factory() as session:
        cached = await get_cached_llm_response(
            prompt=prompt,
            schema_name=schema_name,
            session=session,
        )
        assert cached is not None
        assert cached["amount"] == "2500.00"
        assert cached["reference"] == "ORDER-9999"


@pytest.mark.asyncio
async def test_golden_run_without_api_key_multilingual_replay() -> None:
    """Acceptance: without API key, golden run works in replay mode across languages."""
    original_deterministic = settings.DEMO_DETERMINISTIC
    original_key = settings.GEMINI_API_KEY
    settings.DEMO_DETERMINISTIC = True
    settings.GEMINI_API_KEY = None

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            support_headers = {"Authorization": "Bearer demo-token-support_agent-1"}
            # 1. English golden run
            await client.post("/api/v1/demo/reset", headers=support_headers)
            en_res = await client.post(
                "/api/v1/agent/messages",
                headers={"Authorization": "Bearer demo-token-merchant-1"},
                json={
                    "message": "My ₹6,000 payment from yesterday is missing from settlement",
                    "language": "en",
                },
            )
            assert en_res.status_code == 200
            en_data = en_res.json()["data"]
            assert en_data["active_case_id"] is not None
            assert en_data["is_replay"] is True
            assert en_data["evidence_summary"]["discrepancy"] == "6000.00"

            # 2. Hindi golden run
            await client.post("/api/v1/demo/reset", headers=support_headers)
            hi_res = await client.post(
                "/api/v1/agent/messages",
                headers={"Authorization": "Bearer demo-token-merchant-1"},
                json={
                    "message": "मेरा ₹६,००० का भुगतान सेटलमेंट में नहीं आया है",
                    "language": "hi",
                },
            )
            assert hi_res.status_code == 200
            hi_data = hi_res.json()["data"]
            assert hi_data["active_case_id"] is not None
            assert hi_data["is_replay"] is True
            assert hi_data["evidence_summary"]["discrepancy"] == "6000.00"

            # 3. Marathi golden run
            await client.post("/api/v1/demo/reset", headers=support_headers)
            mr_res = await client.post(
                "/api/v1/agent/messages",
                headers={"Authorization": "Bearer demo-token-merchant-1"},
                json={
                    "message": "माझे ₹६,००० चे पेमेंट सेटलमेंटमध्ये जमा झालेले नाही",
                    "language": "mr",
                },
            )
            assert mr_res.status_code == 200
            mr_data = mr_res.json()["data"]
            assert mr_data["active_case_id"] is not None
            assert mr_data["is_replay"] is True
            assert mr_data["evidence_summary"]["discrepancy"] == "6000.00"
    finally:
        settings.DEMO_DETERMINISTIC = original_deterministic
        settings.GEMINI_API_KEY = original_key
