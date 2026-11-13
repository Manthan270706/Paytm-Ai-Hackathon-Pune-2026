import base64
import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runner import run_agent_turn
from app.api.v1.schemas import (
    VoiceSessionRequest,
    VoiceSessionResponse,
    VoiceSynthesizeRequest,
    VoiceSynthesizeResponse,
    VoiceTranscribeAudioRequest,
    VoiceTranscribeAudioResponse,
    VoiceTranscriptionRequest,
    VoiceTranscriptionResponse,
)
from app.core.dependencies import AuthContext, get_auth_context
from app.core.response import success_response
from app.db.models import Conversation, Message
from app.db.seed import MERCHANT_ID
from app.db.session import get_db_session
from app.integrations import get_stt_provider, get_tts_provider

logger = logging.getLogger(__name__)

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

    reply_audio_url: str | None = None
    if req.generate_audio:
        try:
            tts = get_tts_provider()
            audio_bytes = await tts.synthesize(reply, language=detected_lang)
            b64_str = base64.b64encode(audio_bytes).decode("ascii")
            reply_audio_url = f"data:audio/wav;base64,{b64_str}"
        except Exception as exc:
            logger.warning("Optional TTS synthesis in voice transcription failed: %s", exc)

    return success_response(
        data=VoiceTranscriptionResponse(
            conversation_id=conv_id,
            reply_text=reply,
            reply_audio_url=reply_audio_url,
            language=detected_lang,
            run_id=agent_run.id,
            active_case_id=active_case_id,
            evidence_summary=recon_summary,
            is_replay=result_state.get("is_replay", False),
            llm_source=result_state.get("llm_source", "SYNTHETIC_DEMO"),
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )


@router.post("/voice/transcribe", summary="Transcribe speech audio bytes to text")
async def transcribe_voice(
    req: VoiceTranscribeAudioRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict:
    try:
        audio_bytes = base64.b64decode(req.audio_base64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 audio payload") from exc

    stt = get_stt_provider()
    transcript = await stt.transcribe(audio_bytes, language=req.language)
    source = getattr(stt, "last_source", "mock")

    return success_response(
        data=VoiceTranscribeAudioResponse(
            transcript=transcript,
            language=req.language or "en",
            source=source,
        ).model_dump(),
        source_type="SYNTHETIC_DEMO" if source == "mock" else "SARVAM_AI",
    )


@router.post("/voice/synthesize", summary="Synthesize text to speech")
async def synthesize_voice(
    req: VoiceSynthesizeRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict:
    tts = get_tts_provider()
    audio_bytes = await tts.synthesize(req.text, language=req.language)
    source = getattr(tts, "last_source", "mock")
    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")

    return success_response(
        data=VoiceSynthesizeResponse(
            audio_base64=audio_b64,
            format="audio/wav",
            language=req.language,
            source=source,
        ).model_dump(),
        source_type="SYNTHETIC_DEMO" if source == "mock" else "SARVAM_AI",
    )


@router.get("/voice/tts/audio", summary="Stream synthesized audio as WAV")
async def stream_synthesized_audio(
    text: str = Query(..., description="Text to synthesize"),
    language: str = Query("en", description="Target language (en, hi, mr)"),
    auth: Annotated[AuthContext, Depends(get_auth_context)] = None,  # type: ignore[assignment]
) -> Response:
    tts = get_tts_provider()
    audio_bytes = await tts.synthesize(text, language=language)
    return Response(content=audio_bytes, media_type="audio/wav")
