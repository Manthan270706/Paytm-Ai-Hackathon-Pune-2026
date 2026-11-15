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


class OllamaLLMProvider(LLMProvider):
    """Local Ollama LLM provider adapter running zero-network offline inference.
    
    Conforms to PRD §12.1 and §12.2. All vendor code remains strictly isolated
    within app/integrations/ollama/.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 20.0,
    ) -> None:
        raw_url = base_url or getattr(settings, "OLLAMA_BASE_URL", getattr(settings, "LOCAL_LLM_BASE_URL", "http://localhost:11434"))
        self.base_url = raw_url.rstrip("/")
        # Normalize: if URL ended in /v1, strip it for native API endpoints
        if self.base_url.endswith("/v1"):
            self.native_base = self.base_url[:-3]
            self.v1_base = self.base_url
        else:
            self.native_base = self.base_url
            self.v1_base = f"{self.base_url}/v1"

        self.model = model or getattr(settings, "OLLAMA_MODEL", getattr(settings, "LOCAL_LLM_MODEL", "qwen2.5:3b"))
        self.timeout = timeout

    async def is_available(self) -> bool:
        """Fast liveness probe to verify if local Ollama daemon is running."""
        probe_url = f"{self.native_base}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=0.8) as client:
                res = await client.get(probe_url)
                return res.status_code == 200
        except Exception:
            return False

    async def warmup(self) -> bool:
        """Pre-load model weights into local memory for sub-second first-turn response."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "model": self.model,
                    "prompt": "",
                    "keep_alive": "10m",
                }
                res = await client.post(f"{self.native_base}/api/generate", json=payload)
                return res.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama warmup probe skipped: {e}")
            return False

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.0,
        session: Any | None = None,
    ) -> T:
        """Generate structured Pydantic response from Ollama via constrained JSON format."""
        schema_json = schema.model_json_schema()
        instructions = (
            f"{system_prompt or ''}\n\n"
            f"You MUST respond ONLY with valid JSON conforming to the following JSON Schema:\n"
            f"{json.dumps(schema_json)}\n"
            f"Do not include markdown codeblocks, explanations, or text outside the JSON."
        )

        # 1. First attempt: Native Ollama Chat API with format='json'
        native_endpoint = f"{self.native_base}/api/chat"
        native_payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": prompt},
            ],
            "format": "json",
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        max_attempts = 2
        last_error: Exception | None = None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(max_attempts):
                try:
                    res = await client.post(native_endpoint, json=native_payload)
                    res.raise_for_status()
                    data = res.json()
                    content = data.get("message", {}).get("content", "{}")
                    clean_json = re.sub(
                        r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.MULTILINE
                    )
                    parsed_dict = json.loads(clean_json)
                    return schema.model_validate(parsed_dict)
                except Exception as e:
                    last_error = e
                    # Try OpenAI compatibility endpoint on attempt 2
                    if attempt == 0:
                        v1_endpoint = f"{self.v1_base}/chat/completions"
                        v1_payload = {
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": instructions},
                                {"role": "user", "content": prompt},
                            ],
                            "temperature": temperature,
                            "response_format": {"type": "json_object"},
                        }
                        try:
                            v1_res = await client.post(v1_endpoint, json=v1_payload)
                            v1_res.raise_for_status()
                            v1_data = v1_res.json()
                            content = v1_data["choices"][0]["message"]["content"]
                            clean_json = re.sub(
                                r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.MULTILINE
                            )
                            parsed_dict = json.loads(clean_json)
                            return schema.model_validate(parsed_dict)
                        except Exception as v1_e:
                            last_error = v1_e
                            await asyncio.sleep(0.5)

        raise RuntimeError(f"Ollama local inference failed for model '{self.model}': {last_error}")
