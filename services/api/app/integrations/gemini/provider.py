import asyncio
import json
import logging
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.integrations.base import LLMProvider
from app.integrations.gemini.cache import (
    get_cached_llm_response,
    store_cached_llm_response,
)
from app.integrations.mock import MockLLMProvider

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GeminiLLMProvider(LLMProvider):
    """Google Gemini live adapter with bounded retry and structured Pydantic output."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or getattr(settings, "GEMINI_MODEL", "gemini-3.5-flash-lite")
        self.endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        )

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.0,
        session: Any | None = None,
    ) -> T:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        schema_json = schema.model_json_schema()
        instructions = (
            f"{system_prompt or ''}\n\n"
            f"You MUST respond ONLY with valid JSON conforming to the following JSON Schema:\n"
            f"{json.dumps(schema_json)}\n"
            f"Do not include markdown codeblocks or extra text."
        )

        request_body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": instructions}]},
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }

        # Bounded retry with backoff and model cascade (PRD §12.2)
        models_to_try = [self.model]
        if self.model != "gemini-3.5-flash-lite":
            models_to_try.append("gemini-3.5-flash-lite")

        max_attempts = 2
        last_error: Exception | None = None

        async with httpx.AsyncClient(timeout=8.0) as client:
            for model_name in models_to_try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                for attempt in range(max_attempts):
                    try:
                        res = await client.post(
                            f"{endpoint}?key={self.api_key}",
                            json=request_body,
                            headers={"Content-Type": "application/json"},
                        )
                        res.raise_for_status()
                        data = res.json()

                        # Extract raw text from candidates
                        candidate = data.get("candidates", [])[0]
                        raw_text = candidate.get("content", {}).get("parts", [])[0].get("text", "{}")

                        # Strip code block wrapping if present
                        clean_json = re.sub(
                            r"^```(?:json)?\s*|\s*```$", "", raw_text.strip(), flags=re.MULTILINE
                        )
                        parsed_dict = json.loads(clean_json)
                        return schema.model_validate(parsed_dict)
                    except Exception as e:
                        last_error = e
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(0.5 * (2**attempt))
                        else:
                            break

        raise RuntimeError(f"Gemini API request failed across models {models_to_try}: {last_error}")


class FallbackLLMProvider(LLMProvider):
    """Reliability Fallback Chain (PRD §12.2, §12.3).

    Chain Order:
    1. Local LLM (if enabled and running locally via Ollama / LM Studio)
    2. Groq Cloud LPU (if GROQ_API_KEY is configured)
    3. Gemini Live API (if GEMINI_API_KEY is configured)
    4. Deterministic LLM Cache & Golden Recorded Fixtures
    5. Safe Mock Provider Fallback
    """

    def __init__(self, api_key: str | None = None) -> None:
        from app.integrations.groq.provider import GroqLLMProvider, LocalLLMProvider

        self.local = LocalLLMProvider()
        self.groq = GroqLLMProvider()
        self.gemini = GeminiLLMProvider(api_key=api_key or getattr(settings, "GEMINI_API_KEY", None))
        self.mock = MockLLMProvider()
        self.last_served_from: str = "MOCK"  # "LOCAL", "GROQ", "LIVE", "CACHE", "MOCK"
        self.last_was_replay: bool = False

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.0,
        session: Any = None,
    ) -> T:
        schema_name = schema.__name__

        # Mode A: DEMO_DETERMINISTIC=True (Reliability Mode per PRD §12.3)
        if settings.DEMO_DETERMINISTIC:
            # 1. Check cache first (recorded golden fixtures & DB)
            cached = await get_cached_llm_response(
                prompt=prompt,
                schema_name=schema_name,
                system_prompt=system_prompt,
                session=session,
            )
            if cached is not None:
                self.last_served_from = "CACHE"
                self.last_was_replay = True
                return schema.model_validate(cached)

            # 2. If local or cloud available, attempt live with temperature 0 and cache response
            if getattr(settings, "LOCAL_LLM_ENABLED", False) and await self.local.is_available():
                try:
                    res = await self.local.generate_structured(
                        prompt=prompt,
                        schema=schema,
                        system_prompt=system_prompt,
                        temperature=0.0,
                    )
                    await store_cached_llm_response(
                        prompt=prompt,
                        schema_name=schema_name,
                        response_json=res.model_dump(),
                        system_prompt=system_prompt,
                        session=session,
                    )
                    self.last_served_from = "LOCAL"
                    self.last_was_replay = False
                    return res
                except Exception as e:
                    logger.debug(f"Deterministic live Local LLM attempt skipped: {e}")

            if getattr(settings, "GROQ_API_KEY", None):
                try:
                    res = await self.groq.generate_structured(
                        prompt=prompt,
                        schema=schema,
                        system_prompt=system_prompt,
                        temperature=0.0,
                    )
                    await store_cached_llm_response(
                        prompt=prompt,
                        schema_name=schema_name,
                        response_json=res.model_dump(),
                        system_prompt=system_prompt,
                        session=session,
                    )
                    self.last_served_from = "GROQ"
                    self.last_was_replay = False
                    return res
                except Exception as e:
                    logger.debug(f"Deterministic live Groq attempt skipped: {e}")

            if getattr(settings, "GEMINI_API_KEY", None):
                try:
                    res = await self.gemini.generate_structured(
                        prompt=prompt,
                        schema=schema,
                        system_prompt=system_prompt,
                        temperature=0.0,
                    )
                    await store_cached_llm_response(
                        prompt=prompt,
                        schema_name=schema_name,
                        response_json=res.model_dump(),
                        system_prompt=system_prompt,
                        session=session,
                    )
                    self.last_served_from = "LIVE"
                    self.last_was_replay = False
                    return res
                except Exception as e:
                    logger.debug(f"Deterministic live Gemini attempt skipped: {e}")

            # 3. Fallback to mock
            self.last_served_from = "MOCK"
            self.last_was_replay = True
            return await self.mock.generate_structured(
                prompt=prompt,
                schema=schema,
                system_prompt=system_prompt,
                temperature=0.0,
            )

        # Mode B: Standard Live Flow
        # Tier 1: Local LLM (if enabled and online)
        if getattr(settings, "LOCAL_LLM_ENABLED", False):
            if await self.local.is_available():
                try:
                    res = await self.local.generate_structured(
                        prompt=prompt,
                        schema=schema,
                        system_prompt=system_prompt,
                        temperature=temperature,
                    )
                    self.last_served_from = "LOCAL"
                    self.last_was_replay = False
                    return res
                except Exception as e:
                    logger.warning(
                        f"Local LLM call failed ({e}); falling back to Groq Cloud"
                    )

        # Tier 2: Groq Cloud LPU
        if getattr(settings, "GROQ_API_KEY", None):
            try:
                res = await self.groq.generate_structured(
                    prompt=prompt,
                    schema=schema,
                    system_prompt=system_prompt,
                    temperature=temperature,
                )
                self.last_served_from = "GROQ"
                self.last_was_replay = False
                return res
            except Exception as e:
                logger.warning(
                    f"Groq live call failed ({e}); falling back to next provider"
                )

        # Tier 3: Gemini Live
        if getattr(settings, "GEMINI_API_KEY", None):
            try:
                res = await self.gemini.generate_structured(
                    prompt=prompt,
                    schema=schema,
                    system_prompt=system_prompt,
                    temperature=temperature,
                )
                self.last_served_from = "LIVE"
                self.last_was_replay = False
                return res
            except Exception as e:
                logger.warning(
                    f"Gemini live call failed ({e}); falling back to deterministic cache"
                )

        # Tier 4: Fallback to Cache
        cached = await get_cached_llm_response(
            prompt=prompt,
            schema_name=schema_name,
            system_prompt=system_prompt,
            session=session,
        )
        if cached is not None:
            self.last_served_from = "CACHE"
            self.last_was_replay = True
            return schema.model_validate(cached)

        # Tier 5: Final Fallback to Safe Mock
        self.last_served_from = "MOCK"
        self.last_was_replay = False
        return await self.mock.generate_structured(
            prompt=prompt,
            schema=schema,
            system_prompt=system_prompt,
            temperature=temperature,
        )
