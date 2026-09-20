from __future__ import annotations

import os

from .embeddings import NVIDIA_BASE_URL

NVIDIA_LLM_MODEL = "openai/gpt-oss-20b"


class NvidiaChatLLM:
    """NVIDIA NIM chat-completions backend with a callable interface."""

    def __init__(
        self,
        model_name: str = NVIDIA_LLM_MODEL,
        api_key: str | None = None,
        base_url: str | None = None,
        client=None,
    ) -> None:
        self.model_name = model_name
        self._backend_name = model_name
        self.client = client

        if self.client is not None:
            return

        from openai import OpenAI

        resolved_api_key = api_key or os.getenv("NVIDIA_API_KEY")
        if not resolved_api_key:
            raise RuntimeError("NVIDIA_API_KEY is required for NvidiaChatLLM")

        self.client = OpenAI(
            base_url=base_url or os.getenv("NVIDIA_BASE_URL", NVIDIA_BASE_URL),
            api_key=resolved_api_key,
        )

    def __call__(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=1024,
            reasoning_effort="low",
        )
        return (response.choices[0].message.content or "").strip()
