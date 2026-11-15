import asyncio
import json
import logging
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.integrations.base import LLMProvider

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GroqLLMProvider(LLMProvider):
    """Groq Cloud LPU inference adapter with high throughput and structured Pydantic output."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.GROQ_API_KEY
        self.model = model or getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant")
        self.base_url = (base_url or getattr(settings, "GROQ_BASE_URL", "https://api.groq.com/openai/v1")).rstrip("/")
        self.endpoint = f"{self.base_url}/chat/completions"

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.0,
        session: Any | None = None,
    ) -> T:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured")

        schema_json = schema.model_json_schema()
        instructions = (
            f"{system_prompt or ''}\n\n"
            f"You MUST respond ONLY with valid JSON conforming to the following JSON Schema:\n"
            f"{json.dumps(schema_json)}\n"
            f"Do not include markdown codeblocks, explanations, or text outside the JSON."
        )

        request_body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Bounded retry with backoff and model cascade
        models_to_try = [self.model]
        if self.model != "llama-3.1-8b-instant":
            models_to_try.append("llama-3.1-8b-instant")

        max_attempts = 2
        last_error: Exception | None = None

        async with httpx.AsyncClient(timeout=10.0) as client:
            for model_name in models_to_try:
                request_body["model"] = model_name
                for attempt in range(max_attempts):
                    try:
                        res = await client.post(self.endpoint, json=request_body, headers=headers)
                        res.raise_for_status()
                        data = res.json()

                        content = data["choices"][0]["message"]["content"]
                        clean_json = re.sub(
                            r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.MULTILINE
                        )
                        parsed_dict = json.loads(clean_json)
                        return schema.model_validate(parsed_dict)
                    except Exception as e:
                        last_error = e
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(0.5 * (2**attempt))
                        else:
                            break

        raise RuntimeError(f"Groq API request failed across models {models_to_try}: {last_error}")


class LocalLLMProvider(LLMProvider):
    """Local OpenAI-compatible adapter for Ollama / LM Studio running offline on local machine."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.base_url = (base_url or getattr(settings, "LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")).rstrip("/")
        self.model = model or getattr(settings, "LOCAL_LLM_MODEL", "qwen2.5:3b")
        self.api_key = api_key or getattr(settings, "LOCAL_LLM_API_KEY", "ollama")
        self.endpoint = f"{self.base_url}/chat/completions"

    async def is_available(self) -> bool:
        """Fast liveness probe to verify if local Ollama daemon is active."""
        probe_url = f"{self.base_url}/models"
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                res = await client.get(probe_url, headers={"Authorization": f"Bearer {self.api_key}"})
                return res.status_code == 200
        except Exception:
            return False

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.0,
        session: Any | None = None,
    ) -> T:
        schema_json = schema.model_json_schema()
        instructions = (
            f"{system_prompt or ''}\n\n"
            f"You MUST respond ONLY with valid JSON conforming to the following JSON Schema:\n"
            f"{json.dumps(schema_json)}\n"
            f"Do not include markdown codeblocks, explanations, or text outside the JSON."
        )

        request_body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            res = await client.post(self.endpoint, json=request_body, headers=headers)
            res.raise_for_status()
            data = res.json()

            content = data["choices"][0]["message"]["content"]
            clean_json = re.sub(
                r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.MULTILINE
            )
            parsed_dict = json.loads(clean_json)
            return schema.model_validate(parsed_dict)
