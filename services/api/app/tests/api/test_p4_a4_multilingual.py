import re
import uuid
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.agents.templates import (
    detect_language,
    normalize_devanagari_digits,
    render_investigation_reply,
    render_pending_approval_reply,
    render_verified_reply,
)
from app.db.models import Conversation
from app.main import app
from app.tests.conftest import shared_session_factory

pytestmark = pytest.mark.asyncio


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer demo-token-merchant-1"}


@pytest.fixture
def support_headers() -> dict[str, str]:
    return {"Authorization": "Bearer demo-token-support_agent-1"}


async def test_detect_language_and_devanagari_normalization() -> None:
    """Verify script and marker-based language detection and digit normalization."""
    # 1. English
    assert detect_language("My ₹6,000 payment is missing from settlement") == "en"
    assert detect_language("What is my batch status?") == "en"

    # 2. Hindi
    assert detect_language("मेरा ₹6,000 का सेटलमेंट क्यों रुका हुआ है?") == "hi"
    assert detect_language("भुगतान सेटलमेंट में नहीं आया") == "hi"

    # 3. Marathi
    assert detect_language("माझे ₹६,००० चे पेमेंट सेटलमेंटमध्ये जमा झालेले नाही") == "mr"
    assert detect_language("माझा ₹६,००० चा सेटलमेंट का अडकला आहे?") == "mr"
    assert detect_language("पैसे कधी मिळतील?") == "mr"

    # 4. Devanagari digit normalization
    dev_str = "माझे ₹६,००० आणि ₹१५,०००"
    norm_str = normalize_devanagari_digits(dev_str)
    assert "₹6,000" in norm_str
    assert "₹15,000" in norm_str


async def test_templates_preserve_numbers_and_ids() -> None:
    """Verify templates guarantee identical numerical values and case tags across en, hi, mr."""
    test_amount = "6000.00"
    test_case_id = str(uuid.uuid4())
    expected_tag = test_case_id[:8]

    # Investigation replies
    reply_en = render_investigation_reply("en", test_amount, test_case_id)
    reply_hi = render_investigation_reply("hi", test_amount, test_case_id)
    reply_mr = render_investigation_reply("mr", test_amount, test_case_id)

    for reply in (reply_en, reply_hi, reply_mr):
        assert f"₹{test_amount}" in reply
        assert f"#{expected_tag}" in reply

    # Verified replies
    v_en = render_verified_reply("en", test_amount, test_case_id)
    v_hi = render_verified_reply("hi", test_amount, test_case_id)
    v_mr = render_verified_reply("mr", test_amount, test_case_id)

    for v_reply in (v_en, v_hi, v_mr):
        assert f"₹{test_amount}" in v_reply
        assert f"#{expected_tag}" in v_reply

    # Pending approval replies
    p_en = render_pending_approval_reply("en", test_amount, test_case_id)
    p_hi = render_pending_approval_reply("hi", test_amount, test_case_id)
    p_mr = render_pending_approval_reply("mr", test_amount, test_case_id)

    for p_reply in (p_en, p_hi, p_mr):
        assert f"₹{test_amount}" in p_reply
        assert f"#{expected_tag}" in p_reply


async def test_conversation_stores_detected_language(
    auth_headers: dict[str, str],
    support_headers: dict[str, str],
) -> None:
    """Verify that detected language is stored directly on Conversation in PostgreSQL."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Reset DB first
        await client.post("/api/v1/demo/reset", headers=support_headers)

        # 1. Hindi message
        res_hi = await client.post(
            "/api/v1/agent/messages",
            headers=auth_headers,
            json={"message": "मेरा ₹6,000 का सेटलमेंट नहीं मिला"},
        )
        assert res_hi.status_code == 200
        data_hi = res_hi.json()["data"]
        conv_id_hi = uuid.UUID(data_hi["conversation_id"])
        assert data_hi["language"] == "hi"

        # Verify DB Conversation record
        async with shared_session_factory() as session:
            stmt = select(Conversation).where(Conversation.id == conv_id_hi)
            conv_record = (await session.execute(stmt)).scalars().first()
            assert conv_record is not None
            assert conv_record.language == "hi"

        # 2. Marathi message
        res_mr = await client.post(
            "/api/v1/agent/messages",
            headers=auth_headers,
            json={"message": "माझे ₹६,००० चे पेमेंट सेटलमेंटमध्ये जमा झालेले नाही"},
        )
        assert res_mr.status_code == 200
        data_mr = res_mr.json()["data"]
        conv_id_mr = uuid.UUID(data_mr["conversation_id"])
        assert data_mr["language"] == "mr"

        async with shared_session_factory() as session:
            stmt = select(Conversation).where(Conversation.id == conv_id_mr)
            conv_record_mr = (await session.execute(stmt)).scalars().first()
            assert conv_record_mr is not None
            assert conv_record_mr.language == "mr"


async def test_acceptance_same_case_answered_in_en_hi_mr_shows_identical_numbers(
    auth_headers: dict[str, str],
    support_headers: dict[str, str],
) -> None:
    """Acceptance: the same case answered in English, Hindi, and Marathi shows identical numbers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Reset DB to ensure fresh frozen scenario
        await client.post("/api/v1/demo/reset", headers=support_headers)

        # 1. English run
        res_en = await client.post(
            "/api/v1/agent/messages",
            headers=auth_headers,
            json={"message": "My ₹6,000 payment from yesterday is missing from settlement"},
        )
        assert res_en.status_code == 200
        data_en = res_en.json()["data"]

        # 2. Hindi run
        res_hi = await client.post(
            "/api/v1/agent/messages",
            headers=auth_headers,
            json={"message": "मेरा ₹6,000 का सेटलमेंट नहीं मिला"},
        )
        assert res_hi.status_code == 200
        data_hi = res_hi.json()["data"]

        # 3. Marathi run
        res_mr = await client.post(
            "/api/v1/agent/messages",
            headers=auth_headers,
            json={"message": "माझे ₹६,००० चे पेमेंट सेटलमेंटमध्ये जमा झालेले नाही"},
        )
        assert res_mr.status_code == 200
        data_mr = res_mr.json()["data"]

        # Verify numerical entities across all 3 responses
        amount_pattern = re.compile(r"₹\s*([0-9]+(?:\.[0-9]{2})?)")

        match_en = amount_pattern.search(data_en["reply"])
        match_hi = amount_pattern.search(data_hi["reply"])
        match_mr = amount_pattern.search(data_mr["reply"])

        assert match_en is not None
        assert match_hi is not None
        assert match_mr is not None

        amount_en = match_en.group(1)
        amount_hi = match_hi.group(1)
        amount_mr = match_mr.group(1)

        # Strict parity assertion: identical amounts in all 3 languages
        assert amount_en == "6000.00"
        assert amount_hi == "6000.00"
        assert amount_mr == "6000.00"
        assert amount_en == amount_hi == amount_mr

        # Verify backend evidence summary numbers are Decimal-exact across all 3 runs
        for data in (data_en, data_hi, data_mr):
            evidence = data["evidence_summary"]
            assert Decimal(evidence["expected_net"]) == Decimal("15000.00")
            assert Decimal(evidence["observed_net"]) == Decimal("9000.00")
            assert Decimal(evidence["discrepancy"]) == Decimal("6000.00")
            assert evidence["reason_code"] == "OVERDUE"


async def test_voice_multilingual_continuity(
    auth_headers: dict[str, str],
) -> None:
    """Verify voice session and transcription maintain multilingual continuity."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Hindi voice session
        sess_hi = await client.post(
            "/api/v1/voice/sessions",
            headers=auth_headers,
            json={"language": "hi"},
        )
        assert sess_hi.status_code == 200
        d_hi = sess_hi.json()["data"]
        assert "नमस्ते" in d_hi["welcome_message"]
        conv_id = d_hi["conversation_id"]

        # Hindi voice transcription
        trans_hi = await client.post(
            "/api/v1/voice/transcriptions",
            headers=auth_headers,
            json={
                "conversation_id": conv_id,
                "transcript": "मेरा ₹6,000 का भुगतान सेटलमेंट में नहीं आया है",
                "language": "hi",
            },
        )
        assert trans_hi.status_code == 200
        res_data = trans_hi.json()["data"]
        assert res_data["language"] == "hi"
        assert "₹6000.00" in res_data["reply_text"]
        assert "जांच" in res_data["reply_text"]
