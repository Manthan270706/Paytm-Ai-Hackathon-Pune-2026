import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runner import run_agent_turn
from app.api.v1.schemas import (
    VoiceSessionRequest,
    VoiceSessionResponse,
    VoiceTranscriptionRequest,
    VoiceTranscriptionResponse,
)
from app.core.dependencies import AuthContext, get_auth_context
from app.core.response import success_response
from app.db.models import Conversation, Message
from app.db.seed import MERCHANT_ID
from app.db.session import get_db_session

router = APIRouter()


@router.post("/voice/sessions", summary="Create voice session with AI-identity disclosure")
async def create_voice_session(
    req: VoiceSessionRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    merchant_id = auth.active_merchant_id or MERCHANT_ID
    conv_id = req.conversation_id or uuid.uuid4()

    # Find or create conversation with VOICE channel
    conv_stmt = select(Conversation).where(
        Conversation.id == conv_id,
        Conversation.merchant_id == merchant_id,
    )
    conv = (await session.execute(conv_stmt)).scalars().first()

    now = datetime.now(UTC)
    if conv is None:
        conv = Conversation(
            id=conv_id,
            merchant_id=merchant_id,
            channel="VOICE",
            language=req.language or "en",
            created_at=now,
        )
        session.add(conv)
    else:
        conv.channel = "VOICE"
        if req.language:
            conv.language = req.language

    # Record AI-identity disclosure per PRD §5.2 / §9
    disclosure_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        role="SYSTEM",
        content="AI-identity disclosed: OpsSaathi AI operations teammate (voice session)",
        language=conv.language,
        created_at=now,
    )
    session.add(disclosure_msg)
    await session.commit()

    lang = req.language.lower() if req.language else "en"
    if lang == "hi":
        welcome = (
            "नमस्ते, मैं ऑप्ससाथी हूँ, आपका पेटीएम एआई ऑपरेशंस साथी। "
            "मैं आज आपकी क्या सहायता कर सकता हूँ?"
        )
    elif lang == "mr":
        welcome = (
            "नमस्ते, मी ऑप्ससाथी आहे, तुमचा पेटीएम एआय ऑपरेशन्स सहकारी. "
            "मी आज आपल्याला कशी मदत करू शकतो?"
        )
    else:
        welcome = (
            "Namaste, I am OpsSaathi, your Paytm AI operations teammate. "
            "How can I help you today?"
        )

    return success_response(
        data=VoiceSessionResponse(
            session_id=uuid.uuid4(),
            conversation_id=conv.id,
            ai_identity_disclosed=True,
            welcome_message=welcome,
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )


@router.post("/voice/transcriptions", summary="Submit speech transcript into conversation context")
async def process_voice_transcription(
    req: VoiceTranscriptionRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    merchant_id = auth.active_merchant_id or MERCHANT_ID
    agent_run, result_state = await run_agent_turn(
        merchant_id=merchant_id,
        message=req.transcript,
        session=session,
        conversation_id=req.conversation_id,
        language=req.language,
        user_id=auth.user_id,
    )

    conv_id = result_state.get("conversation_id", req.conversation_id)
    reply = result_state.get("final_reply", "I have investigated your settlement records.")
    detected_lang = result_state.get("language", req.language)
    active_case_id = result_state.get("active_case_id")
    recon_summary = (
        result_state.get("evidence_summary") or result_state.get("reconciliation_summary")
    )
    await session.commit()

    return success_response(
        data=VoiceTranscriptionResponse(
            conversation_id=conv_id,
            reply_text=reply,
            reply_audio_url=None,
            language=detected_lang,
            run_id=agent_run.id,
            active_case_id=active_case_id,
            evidence_summary=recon_summary,
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )
