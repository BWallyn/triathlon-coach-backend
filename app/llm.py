"""
LLM client abstraction.

Configure via environment variables:
  LLM_PROVIDER = "anthropic" | "openai"   (default: anthropic)
  ANTHROPIC_API_KEY = sk-ant-...
  OPENAI_API_KEY    = sk-...
  LLM_MODEL         = override the default model (optional)
"""
# =================
# ==== IMPORTS ====
# =================

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any


# =================
# ==== CLASSES ====
# =================

# Abstract base

class LLMClient(ABC):
    """Single-method interface: send a prompt, get a text response."""

    @abstractmethod
    async def complete(self, system: str, user: str) -> str:
        """Return the assistant's text reply."""

    async def complete_json(self, system: str, user: str) -> Any:
        """Return parsed JSON. Raises ValueError if the reply is not valid JSON."""
        raw = await self.complete(system, user)
        # Strip markdown fences if the model wrapped the JSON
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            cleaned = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        return json.loads(cleaned)


# Anthropic implementation

class AnthropicClient(LLMClient):
    DEFAULT_MODEL = "claude-sonnet-4-6"

    def __init__(self) -> None:
        try:
            import anthropic  # type: ignore
        except ImportError as e:
            raise RuntimeError("Install 'anthropic' package: pip install anthropic") from e

        api_key = os.environ["ANTHROPIC_API_KEY"]
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = os.getenv("LLM_MODEL", self.DEFAULT_MODEL)

    async def complete(self, system: str, user: str) -> str:
        message = await self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text


# OpenAI implementation

class OpenAIClient(LLMClient):
    DEFAULT_MODEL = "gpt-4o"

    def __init__(self) -> None:
        try:
            from openai import AsyncOpenAI  # type: ignore
        except ImportError as e:
            raise RuntimeError("Install 'openai' package: pip install openai") from e

        api_key = os.environ["OPENAI_API_KEY"]
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = os.getenv("LLM_MODEL", self.DEFAULT_MODEL)

    async def complete(self, system: str, user: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""


# Factory

def get_llm_client() -> LLMClient:
    """
    FastAPI dependency. Returns the configured LLM client.
    Raises a clear RuntimeError if the provider or API key is missing.
    """
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    if provider == "anthropic":
        return AnthropicClient()
    if provider == "openai":
        return OpenAIClient()
    raise RuntimeError(f"Unknown LLM_PROVIDER '{provider}'. Choose 'anthropic' or 'openai'.")
