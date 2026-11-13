import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.models import Conversation, Message
from app.db.seed import MERCHANT_ID
from app.main import app
from app.tests.conftest import shared_session_factory


@pytest.mark.asyncio
async def test_voice_session_ai_disclosure() -> None:
    """Voice session records AI-identity disclosure and returns localized welcome message."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. English session
        res_en = await client.post(
            "/api/v1/voice/sessions",
            headers={"Authorization": "Bearer demo-token-merchant-1"},
            json={"language": "en"},
        )
        assert res_en.status_code == 200
        data_en = res_en.json()["data"]
        assert data_en["ai_identity_disclosed"] is True
        assert "OpsSaathi" in data_en["welcome_message"]
        assert "AI" in data_en["welcome_message"]
        conv_id = uuid.UUID(data_en["conversation_id"])

        # 2. Hindi session
        res_hi = await client.post(
            "/api/v1/voice/sessions",
            headers={"Authorization": "Bearer demo-token-merchant-1"},
            json={"conversation_id": str(conv_id), "language": "hi"},
        )
        assert res_hi.status_code == 200
        data_hi = res_hi.json()["data"]
        assert data_hi["ai_identity_disclosed"] is True
        assert "ऑप्ससाथी" in data_hi["welcome_message"]

        # 3. Marathi session
        res_mr = await client.post(
            "/api/v1/voice/sessions",
            headers={"Authorization": "Bearer demo-token-merchant-1"},
            json={"language": "mr"},
        )
        assert res_mr.status_code == 200
        assert "ऑप्ससाथी" in res_mr.json()["data"]["welcome_message"]

    # Verify disclosure message is recorded in DB
    async with shared_session_factory() as session:
        msgs = (
            await session.execute(
                select(Message).where(
                    Message.conversation_id == conv_id,
                    Message.role == "SYSTEM",
                )
            )
        ).scalars().all()
        assert len(msgs) >= 1
        assert "AI-identity disclosed" in msgs[0].content


@pytest.mark.asyncio
async def test_chat_to_voice_channel_continuity() -> None:
    """Start in chat, continue in voice: active case and conversation context are preserved."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Start complaint via chat
        chat_res = await client.post(
            "/api/v1/agent/messages",
            headers={"Authorization": "Bearer demo-token-merchant-1"},
            json={
                "message": "My ₹6,000 payment from yesterday is missing from settlement",
                "language": "en",
            },
        )
        assert chat_res.status_code == 200
        chat_data = chat_res.json()["data"]
        conv_id = chat_data["conversation_id"]
        active_case_id = chat_data["active_case_id"]
        assert active_case_id is not None

        # 2. Continue in voice session on the same conversation
        voice_session_res = await client.post(
            "/api/v1/voice/sessions",
            headers={"Authorization": "Bearer demo-token-merchant-1"},
            json={"conversation_id": conv_id, "language": "en"},
        )
        assert voice_session_res.status_code == 200
        assert voice_session_res.json()["data"]["conversation_id"] == conv_id

        # 3. Submit speech transcript in the same conversation
        trans_res = await client.post(
            "/api/v1/voice/transcriptions",
            headers={"Authorization": "Bearer demo-token-merchant-1"},
            json={
                "conversation_id": conv_id,
                "transcript": "What is the status of my missing ₹6,000 settlement?",
                "language": "en",
            },
        )
        assert trans_res.status_code == 200
        trans_data = trans_res.json()["data"]
        assert trans_data["conversation_id"] == conv_id
        # Continuity preserved: active_case_id is preserved
        assert trans_data["active_case_id"] == active_case_id

    # 4. Verify DB Conversation channel updated and case preserved
    async with shared_session_factory() as session:
        conv = (
            await session.execute(
                select(Conversation).where(
                    Conversation.id == uuid.UUID(conv_id),
                    Conversation.merchant_id == MERCHANT_ID,
                )
            )
        ).scalar_one()
        assert conv.channel == "VOICE"
        assert str(conv.active_case_id) == str(active_case_id)


@pytest.mark.asyncio
async def test_voice_first_complaint_investigation() -> None:
    """A complaint spoken directly via voice initiates investigation, case and evidence summary."""
    conv_id = str(uuid.uuid4())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/demo/reset",
            headers={"Authorization": "Bearer demo-token-support_agent-1"},
        )
        trans_res = await client.post(
            "/api/v1/voice/transcriptions",
            headers={"Authorization": "Bearer demo-token-merchant-1"},
            json={
                "conversation_id": conv_id,
                "transcript": "My ₹6,000 payment from yesterday is missing from settlement",
                "language": "en",
            },
        )
        assert trans_res.status_code == 200
        data = trans_res.json()["data"]
        assert data["active_case_id"] is not None
        assert data["evidence_summary"] is not None
        evidence = data["evidence_summary"]
        assert evidence["expected_net"] == "15000.00"
        assert evidence["observed_net"] == "9000.00"
        assert evidence["discrepancy"] == "6000.00"
