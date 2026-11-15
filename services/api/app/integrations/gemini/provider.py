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
    """Reliability Fallback Chain (PRD §12.2, §12.3, UPSCALE Phase U1).

    Configurable cascade order via LLM_CASCADE env var (e.g. 'groq,ollama,cache,mock').
    Chain Order (Default):
    1. Groq Cloud LPU (if GROQ_API_KEY is configured)
    2. Local Ollama LLM (zero-network offline inference via Qwen 2.5 3B)
    3. Gemini Live API (optional fallback if configured)
    4. Deterministic LLM Cache & Golden Recorded Fixtures
    5. Safe Mock Provider Fallback
    """

    def __init__(self, api_key: str | None = None) -> None:
        from app.integrations.groq.provider import GroqLLMProvider, LocalLLMProvider
        from app.integrations.ollama.provider import OllamaLLMProvider

        self.ollama = OllamaLLMProvider()
        self.local = self.ollama  # Alias for backward compatibility
        self.groq = GroqLLMProvider()
        self.gemini = GeminiLLMProvider(api_key=api_key or getattr(settings, "GEMINI_API_KEY", None))
        self.mock = MockLLMProvider()
        self.last_served_from: str = "MOCK"  # "OLLAMA", "LOCAL", "GROQ", "LIVE", "CACHE", "MOCK"
        self.last_was_replay: bool = False
        self.tier_history: list[dict[str, Any]] = []

    @property
    def cascade_tiers(self) -> list[str]:
        raw = getattr(settings, "LLM_CASCADE", "groq,ollama,cache,mock")
        return [t.strip().lower() for t in raw.split(",") if t.strip()]

    async def warmup(self) -> bool:
        """Startup warm-up call to prime local and cloud LLM tiers."""
        if "ollama" in self.cascade_tiers:
            return await self.ollama.warmup()
        return True

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.0,
        session: Any = None,
    ) -> T:
        schema_name = schema.__name__
        self.tier_history = []

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
                self.tier_history.append({"tier": "cache", "status": "SERVED"})
                return schema.model_validate(cached)

            # 2. If live tiers available, attempt with temperature 0 and cache response
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
                    self.tier_history.append({"tier": "groq", "status": "SERVED"})
                    return res
                except Exception as e:
                    logger.debug(f"Deterministic live Groq attempt skipped: {e}")
                    self.tier_history.append({"tier": "groq", "status": "FAILED", "error": str(e)})

            if await self.ollama.is_available():
                try:
                    res = await self.ollama.generate_structured(
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
                    self.last_served_from = "OLLAMA"
                    self.last_was_replay = False
                    self.tier_history.append({"tier": "ollama", "status": "SERVED"})
                    return res
                except Exception as e:
                    logger.debug(f"Deterministic live Ollama attempt skipped: {e}")
                    self.tier_history.append({"tier": "ollama", "status": "FAILED", "error": str(e)})

            # 3. Fallback to mock
            self.last_served_from = "MOCK"
            self.last_was_replay = True
            self.tier_history.append({"tier": "mock", "status": "SERVED"})
            return await self.mock.generate_structured(
                prompt=prompt,
                schema=schema,
                system_prompt=system_prompt,
                temperature=0.0,
            )

        # Mode B: Dynamic LLM_CASCADE Execution
        for tier in self.cascade_tiers:
            # 1. Groq Cloud LPU
            if tier in {"groq", "groq_cloud"}:
                if not getattr(settings, "GROQ_API_KEY", None):
                    self.tier_history.append({"tier": "groq", "status": "SKIPPED_NO_KEY"})
                    continue
                try:
                    res = await self.groq.generate_structured(
                        prompt=prompt,
                        schema=schema,
                        system_prompt=system_prompt,
                        temperature=temperature,
                    )
                    self.last_served_from = "GROQ"
                    self.last_was_replay = False
                    self.tier_history.append({"tier": "groq", "status": "SERVED"})
                    return res
                except Exception as e:
                    logger.warning(f"Groq cascade call failed ({e}); evaluating next tier")
                    self.tier_history.append({"tier": "groq", "status": "FAILED", "error": str(e)})

            # 2. Local Ollama LLM
            elif tier in {"ollama", "local", "local_llm"}:
                if not await self.ollama.is_available():
                    self.tier_history.append({"tier": "ollama", "status": "SKIPPED_OFFLINE"})
                    continue
                try:
                    res = await self.ollama.generate_structured(
                        prompt=prompt,
                        schema=schema,
                        system_prompt=system_prompt,
                        temperature=temperature,
                    )
                    self.last_served_from = "OLLAMA"
                    self.last_was_replay = False
                    self.tier_history.append({"tier": "ollama", "status": "SERVED"})
                    return res
                except Exception as e:
                    logger.warning(f"Ollama local call failed ({e}); evaluating next tier")
                    self.tier_history.append({"tier": "ollama", "status": "FAILED", "error": str(e)})

            # 3. Gemini Live
            elif tier in {"gemini", "gemini_live"}:
                if not getattr(settings, "GEMINI_API_KEY", None):
                    self.tier_history.append({"tier": "gemini", "status": "SKIPPED_NO_KEY"})
                    continue
                try:
                    res = await self.gemini.generate_structured(
                        prompt=prompt,
                        schema=schema,
                        system_prompt=system_prompt,
                        temperature=temperature,
                    )
                    self.last_served_from = "LIVE"
                    self.last_was_replay = False
                    self.tier_history.append({"tier": "gemini", "status": "SERVED"})
                    return res
                except Exception as e:
                    logger.warning(f"Gemini live call failed ({e}); evaluating next tier")
                    self.tier_history.append({"tier": "gemini", "status": "FAILED", "error": str(e)})

            # 4. Deterministic Cache
            elif tier in {"cache", "llm_cache"}:
                cached = await get_cached_llm_response(
                    prompt=prompt,
                    schema_name=schema_name,
                    system_prompt=system_prompt,
                    session=session,
                )
                if cached is not None:
                    self.last_served_from = "CACHE"
                    self.last_was_replay = True
                    self.tier_history.append({"tier": "cache", "status": "SERVED"})
                    return schema.model_validate(cached)
                self.tier_history.append({"tier": "cache", "status": "MISS"})

            # 5. Safe Mock Provider Fallback
            elif tier in {"mock", "safe_mock"}:
                self.last_served_from = "MOCK"
                self.last_was_replay = False
                self.tier_history.append({"tier": "mock", "status": "SERVED"})
                return await self.mock.generate_structured(
                    prompt=prompt,
                    schema=schema,
                    system_prompt=system_prompt,
                    temperature=temperature,
                )

        # Final guarantee fallback if all configured cascade tiers exhausted
        self.last_served_from = "MOCK"
        self.last_was_replay = False
        self.tier_history.append({"tier": "mock", "status": "EXHAUSTION_FALLBACK"})
        return await self.mock.generate_structured(
            prompt=prompt,
            schema=schema,
            system_prompt=system_prompt,
            temperature=temperature,
        )
