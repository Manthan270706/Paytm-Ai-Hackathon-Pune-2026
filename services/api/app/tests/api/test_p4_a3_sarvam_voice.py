import base64
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.integrations.sarvam.provider import (
    FallbackSpeechToText,
    FallbackTextToSpeech,
    SarvamSpeechToText,
    SarvamTextToSpeech,
)
from app.main import app

pytestmark = pytest.mark.asyncio


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer demo-token-merchant-1"}


async def test_sarvam_adapters_direct_and_fallback() -> None:
    """Verify Sarvam adapters initialization, language mapping, and fallback behavior."""
    stt_empty = SarvamSpeechToText(api_key="")
    assert not stt_empty.is_available()

    tts_empty = SarvamTextToSpeech(api_key="")
    assert not tts_empty.is_available()

    # Fallback adapters should succeed even without keys
    fallback_stt = FallbackSpeechToText(sarvam_stt=stt_empty)
    fallback_tts = FallbackTextToSpeech(sarvam_tts=tts_empty)

    dummy_audio = b"RIFF1234WAVEfmt "
    en_transcript = await fallback_stt.transcribe(dummy_audio, language="en")
    assert "₹6,000" in en_transcript
    assert fallback_stt.last_source == "mock"

    hi_transcript = await fallback_stt.transcribe(dummy_audio, language="hi")
    assert "सेटलमेंट" in hi_transcript

    mr_transcript = await fallback_stt.transcribe(dummy_audio, language="mr")
    assert "सेटलमेंट" in mr_transcript

    audio_bytes = await fallback_tts.synthesize("Test speech", language="en")
    assert audio_bytes.startswith(b"RIFF")
    assert fallback_tts.last_source == "mock"


async def test_sarvam_mocked_http_success() -> None:
    """Verify Sarvam STT and TTS succeed when API returns 200 OK."""
    sarvam_stt = SarvamSpeechToText(api_key="valid-test-key")
    sarvam_tts = SarvamTextToSpeech(api_key="valid-test-key")

    dummy_wav_b64 = base64.b64encode(b"RIFFmockwavheaderdata").decode("ascii")

    async def mock_post(url: str, *args: Any, **kwargs: Any) -> httpx.Response:
        req = httpx.Request("POST", url)
        if "speech-to-text" in url:
            return httpx.Response(
                200,
                json={"transcript": "मेरा ₹6,000 का भुगतान क्यों नहीं हुआ?", "language_code": "hi"},
                request=req,
            )
        elif "text-to-speech" in url:
            return httpx.Response(
                200,
                json={"audios": [dummy_wav_b64]},
                request=req,
            )
        return httpx.Response(404, request=req)

    with patch.object(httpx.AsyncClient, "post", side_effect=mock_post):
        transcript = await sarvam_stt.transcribe(b"dummy-audio", language="hi")
        assert "₹6,000" in transcript

        audio_bytes = await sarvam_tts.synthesize("नमस्ते", language="hi")
        assert audio_bytes == b"RIFFmockwavheaderdata"


async def test_sarvam_http_error_falls_back() -> None:
    """Verify Sarvam HTTP errors trigger fallback cleanly without crashing."""
    sarvam_stt = SarvamSpeechToText(api_key="valid-test-key")
    sarvam_tts = SarvamTextToSpeech(api_key="valid-test-key")

    fallback_stt = FallbackSpeechToText(sarvam_stt=sarvam_stt)
    fallback_tts = FallbackTextToSpeech(sarvam_tts=sarvam_tts)

    async def mock_post_err(url: str, *args: Any, **kwargs: Any) -> httpx.Response:
        req = httpx.Request("POST", url)
        return httpx.Response(500, text="Internal Server Error", request=req)

    with patch.object(httpx.AsyncClient, "post", side_effect=mock_post_err):
        transcript = await fallback_stt.transcribe(b"dummy-audio", language="en")
        assert "₹6,000" in transcript
        assert fallback_stt.last_source == "mock"

        audio_bytes = await fallback_tts.synthesize("Hello", language="en")
        assert audio_bytes.startswith(b"RIFF")
        assert fallback_tts.last_source == "mock"


async def test_voice_api_transcribe_and_synthesize_endpoints(
    auth_headers: dict[str, str],
) -> None:
    """Verify POST /voice/transcribe, /voice/synthesize, and /voice/tts/audio endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Transcribe endpoint
        dummy_b64 = base64.b64encode(b"dummy-audio-bytes").decode("ascii")
        res_transcribe = await client.post(
            "/api/v1/voice/transcribe",
            headers=auth_headers,
            json={"audio_base64": dummy_b64, "language": "hi"},
        )
        assert res_transcribe.status_code == 200
        t_data = res_transcribe.json()["data"]
        assert "transcript" in t_data
        assert t_data["language"] == "hi"

        # 2. Synthesize endpoint
        res_synth = await client.post(
            "/api/v1/voice/synthesize",
            headers=auth_headers,
            json={"text": "Your settlement is processing", "language": "en"},
        )
        assert res_synth.status_code == 200
        s_data = res_synth.json()["data"]
        assert "audio_base64" in s_data
        assert s_data["format"] == "audio/wav"

        # 3. Raw audio streaming endpoint
        res_audio = await client.get(
            "/api/v1/voice/tts/audio?text=Hello+Merchant&language=en",
            headers=auth_headers,
        )
        assert res_audio.status_code == 200
        assert res_audio.headers["content-type"] == "audio/wav"
        assert res_audio.content.startswith(b"RIFF")


async def test_disabling_sarvam_key_preserves_flow(
    auth_headers: dict[str, str],
) -> None:
    """Verify that with SARVAM_API_KEY removed, the entire voice flow completes seamlessly."""
    original_key = settings.SARVAM_API_KEY
    settings.SARVAM_API_KEY = None
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Create voice session
            sess_res = await client.post(
                "/api/v1/voice/sessions",
                headers=auth_headers,
                json={"language": "mr"},
            )
            assert sess_res.status_code == 200
            conv_id = sess_res.json()["data"]["conversation_id"]

            # 2. Submit transcription with audio generation requested
            voice_res = await client.post(
                "/api/v1/voice/transcriptions",
                headers=auth_headers,
                json={
                    "conversation_id": conv_id,
                    "transcript": "माझे ₹६,००० चे पेमेंट का जमा झालेले नाही?",
                    "language": "mr",
                    "generate_audio": True,
                },
            )
            assert voice_res.status_code == 200
            v_data = voice_res.json()["data"]
            assert v_data["conversation_id"] == conv_id
            assert v_data["reply_text"]
            assert v_data["reply_audio_url"] is not None
            assert v_data["reply_audio_url"].startswith("data:audio/wav;base64,")
    finally:
        settings.SARVAM_API_KEY = original_key
