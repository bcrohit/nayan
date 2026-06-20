"""Groq vision service for navigation guidance from camera frames."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from groq import Groq

from app.images import prepare_image_data_url
from app.prompts import load_prompt

logger = logging.getLogger(__name__)


class VisionNotConfiguredError(RuntimeError):
    """Raised when Groq credentials are missing."""


class VisionServiceError(Exception):
    """Raised when the vision model returns an invalid response."""


def parse_json_response(raw_text: str) -> dict[str, Any]:
    """Parse model JSON output, tolerating occasional markdown wrapping."""
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        cleaned = raw_text.strip("`").removeprefix("json").strip()
        return json.loads(cleaned)


class VisionService:
    """Reuses one Groq client for repeated image description requests."""

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        prompt_file: str,
        max_dimension: int,
        rotate_degrees: int,
        max_tokens: int = 150,
    ) -> None:
        self._model = model
        self._prompt = load_prompt(prompt_file)
        self._max_dimension = max_dimension
        self._rotate_degrees = rotate_degrees
        self._max_tokens = max_tokens
        self._client = Groq(api_key=api_key) if api_key else None

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    async def describe(self, image_bytes: bytes) -> dict[str, Any]:
        """Analyze image bytes and return structured navigation guidance."""
        if self._client is None:
            raise VisionNotConfiguredError("GROQ_API_KEY is not configured")

        return await asyncio.to_thread(self._describe_sync, image_bytes)

    def _describe_sync(self, image_bytes: bytes) -> dict[str, Any]:
        data_url = prepare_image_data_url(
            image_bytes,
            max_dimension=self._max_dimension,
            rotate_degrees=self._rotate_degrees,
        )

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self._prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=self._max_tokens,
        )

        raw_text = response.choices[0].message.content
        if not raw_text:
            raise VisionServiceError("Vision model returned an empty response")

        try:
            return parse_json_response(raw_text.strip())
        except json.JSONDecodeError as exc:
            logger.error("Vision model returned invalid JSON", extra={"raw_text": raw_text[:200]})
            raise VisionServiceError("Vision model returned invalid JSON") from exc
