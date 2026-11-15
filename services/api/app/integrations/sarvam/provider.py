import asyncio
import base64
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.integrations.base import SpeechToText, TextToSpeech
from app.integrations.mock import MockSpeechToText, MockTextToSpeech

logger = logging.getLogger(__name__)

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

LANG_MAP_STT: dict[str, str] = {
    "en": "en-IN",
    "hi": "hi-IN",
    "mr": "mr-IN",
}

LANG_MAP_TTS: dict[str, str] = {
    "en": "en-IN",
    "hi": "hi-IN",
    "mr": "mr-IN",
}


class SarvamSpeechToText(SpeechToText):
    """Sarvam AI speech-to-text adapter for Indian languages (en, hi, mr)."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = settings.SARVAM_API_KEY if api_key is None else api_key

    def is_available(self) -> bool:
        return bool(
            self.api_key
            and self.api_key.strip()
            and self.api_key != "YOUR_SARVAM_API_KEY"
        )

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> str:
        if not self.is_available():
            raise ValueError("Sarvam API key is not configured or invalid.")

        target_lang = LANG_MAP_STT.get((language or "en").lower(), "en-IN")
        headers = {
            "api-subscription-key": str(self.api_key),
        }
        files = {
            "file": ("audio.wav", audio_bytes, "audio/wav"),
        }
        data: dict[str, Any] = {
            "model": "saarika:v2",
            "language_code": target_lang,
        }

        # Bounded retry: up to 2 attempts
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        SARVAM_STT_URL,
                        headers=headers,
                        files=files,
                        data=data,
                    )
                    resp.raise_for_status()
                    payload = resp.json()
                    transcript = payload.get("transcript", "")
                    if transcript:
                        return str(transcript)
                    return ""
            except (TimeoutError, httpx.HTTPError) as exc:
                last_exc = exc
                logger.warning(
                    "Sarvam STT attempt %d failed: %s", attempt + 1, exc
                )
                if attempt == 0:
                    await asyncio.sleep(0.5)

        raise RuntimeError(
            f"Sarvam STT failed after bounded retries: {last_exc}"
        ) from last_exc


class SarvamTextToSpeech(TextToSpeech):
    """Sarvam AI text-to-speech adapter for Indian languages (en, hi, mr)."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = settings.SARVAM_API_KEY if api_key is None else api_key

    def is_available(self) -> bool:
        return bool(
            self.api_key
            and self.api_key.strip()
            and self.api_key != "YOUR_SARVAM_API_KEY"
        )

    async def synthesize(
        self,
        text: str,
        language: str = "en",
    ) -> bytes:
        if not self.is_available():
            raise ValueError("Sarvam API key is not configured or invalid.")

        target_lang = LANG_MAP_TTS.get((language or "en").lower(), "en-IN")
        headers = {
            "api-subscription-key": str(self.api_key),
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "inputs": [text[:500]],
            "target_language_code": target_lang,
            "speaker": "ishita",
            "pitch": 0,
            "pace": 1.0,
            "loudness": 1.5,
            "speech_sample_rate": 16000,
            "enable_preprocessing": True,
            "model": "bulbul:v3",
        }

        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        SARVAM_TTS_URL,
                        headers=headers,
                        json=body,
                    )
                    resp.raise_for_status()
                    payload = resp.json()
                    audios = payload.get("audios", [])
                    if audios and isinstance(audios[0], str):
                        return base64.b64decode(audios[0])
                    raise ValueError("No audio returned in Sarvam TTS response.")
            except (TimeoutError, httpx.HTTPError, ValueError) as exc:
                last_exc = exc
                logger.warning(
                    "Sarvam TTS attempt %d failed: %s", attempt + 1, exc
                )
                if attempt == 0:
                    await asyncio.sleep(0.5)

        raise RuntimeError(
            f"Sarvam TTS failed after bounded retries: {last_exc}"
        ) from last_exc


class FallbackSpeechToText(SpeechToText):
    """Fallback chain: Sarvam STT -> MockSpeechToText."""

    def __init__(
        self,
        sarvam_stt: SarvamSpeechToText | None = None,
        mock_stt: MockSpeechToText | None = None,
    ) -> None:
        self.sarvam_stt = sarvam_stt or SarvamSpeechToText()
        self.mock_stt = mock_stt or MockSpeechToText()
        self.last_source = "mock"

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> str:
        if settings.DEMO_DETERMINISTIC:
            self.last_source = "mock"
            return await self.mock_stt.transcribe(audio_bytes, language=language)

        if self.sarvam_stt.is_available():
            try:
                res = await self.sarvam_stt.transcribe(
                    audio_bytes, language=language
                )
                self.last_source = "sarvam"
                return res
            except Exception as exc:
                logger.warning(
                    "Sarvam STT failed, falling back to mock provider: %s", exc
                )

        self.last_source = "mock"
        return await self.mock_stt.transcribe(audio_bytes, language=language)


class FallbackTextToSpeech(TextToSpeech):
    """Fallback chain: Sarvam TTS -> MockTextToSpeech."""

    def __init__(
        self,
        sarvam_tts: SarvamTextToSpeech | None = None,
        mock_tts: MockTextToSpeech | None = None,
    ) -> None:
        self.sarvam_tts = sarvam_tts or SarvamTextToSpeech()
        self.mock_tts = mock_tts or MockTextToSpeech()
        self.last_source = "mock"

    async def synthesize(
        self,
        text: str,
        language: str = "en",
    ) -> bytes:
        if settings.DEMO_DETERMINISTIC:
            self.last_source = "mock"
            return await self.mock_tts.synthesize(text, language=language)

        if self.sarvam_tts.is_available():
            try:
                res = await self.sarvam_tts.synthesize(
                    text, language=language
                )
                self.last_source = "sarvam"
                return res
            except Exception as exc:
                logger.warning(
                    "Sarvam TTS failed, falling back to mock provider: %s", exc
                )

        self.last_source = "mock"
        return await self.mock_tts.synthesize(text, language=language)
