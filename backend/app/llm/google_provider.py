"""Google Gemini implementation of the provider-neutral LLM interface."""

import logging
from typing import Any

import httpx2

from app.llm.base import (
    LLMConfigurationError,
    LLMConnectionError,
    LLMProviderError,
    LLMRateLimitError,
    LLMRequest,
    LLMResponseError,
    LLMResult,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)


class GoogleProvider:
    name = "google"

    def __init__(self, *, api_key: str, model: str, timeout_seconds: float) -> None:
        self.model = model
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def complete(self, request: LLMRequest) -> LLMResult:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        body: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": request.system}]},
            "contents": [
                {"role": m.role, "parts": [{"text": m.content}]}
                for m in request.messages
            ],
            "generationConfig": {
                "maxOutputTokens": request.max_output_tokens,
                "responseMimeType": "application/json",
                "responseJsonSchema": request.json_schema,
            },
        }

        try:
            async with httpx2.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(url, params={"key": self._api_key}, json=body)
                status_code = response.status_code
                response.raise_for_status()
                payload = response.json()
        except httpx2.TimeoutException as exc:
            raise LLMTimeoutError("provider request timed out") from exc
        except httpx2.RequestError as exc:
            raise LLMConnectionError("could not reach the provider") from exc
        except httpx2.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code in (401, 403):
                raise LLMConfigurationError("provider rejected the configured credentials") from exc
            if status_code == 429:
                raise LLMRateLimitError("provider rate limit reached") from exc
            logger.warning("Google provider returned HTTP %s", status_code)
            raise LLMProviderError(
                f"provider returned HTTP {status_code}", status_code=status_code
            ) from exc

        candidates = payload.get("candidates") or []
        if not candidates:
            raise LLMResponseError("model returned no candidates")
        candidate = candidates[0]
        if candidate.get("finishReason") == "MAX_TOKENS":
            raise LLMResponseError("model output was truncated")

        parts = (candidate.get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            raise LLMResponseError("model returned no text")

        usage = payload.get("usageMetadata") or {}
        return LLMResult(
            text=text,
            model=self.model,
            stop_reason=candidate.get("finishReason"),
            input_tokens=usage.get("promptTokenCount"),
            output_tokens=usage.get("candidatesTokenCount"),
        )