import uuid

from fastapi import APIRouter

from app.api.v1.schemas import (
    VoiceSessionRequest,
    VoiceSessionResponse,
    VoiceTranscriptionRequest,
    VoiceTranscriptionResponse,
)
from app.core.response import success_response

router = APIRouter()


@router.post("/voice/sessions", summary="Create voice session with AI-identity disclosure")
async def create_voice_session(req: VoiceSessionRequest) -> dict:
    conversation_id = req.conversation_id or uuid.uuid4()
    return success_response(
        data=VoiceSessionResponse(
            session_id=uuid.uuid4(),
            conversation_id=conversation_id,
            ai_identity_disclosed=True,
            welcome_message=(
                "Namaste, I am OpsSaathi, your Paytm AI operations teammate. "
                "How can I help you today?"
            ),
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )


@router.post("/voice/transcriptions", summary="Submit speech transcript into conversation context")
async def process_voice_transcription(req: VoiceTranscriptionRequest) -> dict:
    return success_response(
        data=VoiceTranscriptionResponse(
            conversation_id=req.conversation_id,
            reply_text=(
                "I heard you say that ₹6,000 is missing. I have retrieved your records "
                "and started the investigation."
            ),
            reply_audio_url=None,
            language=req.language,
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )
