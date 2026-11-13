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

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
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

        # Bounded retry with backoff (PRD §12.2)
        max_attempts = 3
        last_error: Exception | None = None

        async with httpx.AsyncClient(timeout=8.0) as client:
            for attempt in range(max_attempts):
                try:
                    res = await client.post(
                        f"{self.endpoint}?key={self.api_key}",
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

        raise RuntimeError(f"Gemini API request failed after {max_attempts} attempts: {last_error}")


class FallbackLLMProvider(LLMProvider):
    """Reliability Fallback Chain (PRD §12.2, §12.3).

    Chain Order:
    1. Live Gemini (if configured and not forced deterministic)
    2. Deterministic LLM Cache & Golden Recorded Fixtures
    3. Safe Mock Provider Fallback
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.gemini = GeminiLLMProvider(api_key=api_key)
        self.mock = MockLLMProvider()
        self.last_served_from: str = "MOCK"  # "LIVE", "CACHE", "MOCK"
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

            # 2. If key exists, attempt live with temperature 0 and cache response
            if settings.GEMINI_API_KEY:
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
        if settings.GEMINI_API_KEY:
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

        # Fallback to Cache
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

        # Final Fallback to Mock
        self.last_served_from = "MOCK"
        self.last_was_replay = False
        return await self.mock.generate_structured(
            prompt=prompt,
            schema=schema,
            system_prompt=system_prompt,
            temperature=temperature,
        )
