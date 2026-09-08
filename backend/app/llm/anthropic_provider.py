"""Anthropic implementation of the LLM provider interface.

Structured output is requested through the Messages API `output_config.format`
JSON-schema constraint, so the model's answer is a single JSON text block that
the caller still validates locally (the constraint is a strong hint to the
provider, not a trust boundary — AKILI's contract validation is).

The API key is given to the SDK client at construction and appears nowhere
else: not in requests, not in logs, not in errors.
"""

import logging

import anthropic

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


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        client: anthropic.AsyncAnthropic | None = None,
    ) -> None:
        self.model = model
        # `client` is injectable for tests. The SDK retries 408/409/429/5xx and
        # connection errors twice by itself; we do not add another retry layer.
        self._client = client or anthropic.AsyncAnthropic(
            api_key=api_key, timeout=timeout_seconds, max_retries=2
        )

    async def complete(self, request: LLMRequest) -> LLMResult:
        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=request.max_output_tokens,
                system=request.system,
                messages=[{"role": m.role, "content": m.content} for m in request.messages],
                output_config={
                    "format": {"type": "json_schema", "schema": request.json_schema}
                },
            )
        # Most specific first: several of these are subclasses of the later ones.
        except anthropic.APITimeoutError as exc:
            raise LLMTimeoutError("provider request timed out") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMConnectionError("could not reach the provider") from exc
        except anthropic.RateLimitError as exc:
            raise LLMRateLimitError("provider rate limit reached") from exc
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as exc:
            raise LLMConfigurationError("provider rejected the configured credentials") from exc
        except anthropic.APIStatusError as exc:
            logger.warning("Anthropic API returned HTTP %s", exc.status_code)
            raise LLMProviderError(
                f"provider returned HTTP {exc.status_code}", status_code=exc.status_code
            ) from exc
        except anthropic.APIError as exc:
            logger.warning("Anthropic API error: %s", type(exc).__name__)
            raise LLMProviderError("provider error") from exc

        if response.stop_reason == "refusal":
            raise LLMResponseError("model declined to answer")
        if response.stop_reason == "max_tokens":
            raise LLMResponseError("model output was truncated")

        text = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()
        if not text:
            raise LLMResponseError("model returned no text")

        usage = response.usage
        return LLMResult(
            text=text,
            model=response.model,
            stop_reason=response.stop_reason,
            input_tokens=usage.input_tokens if usage else None,
            output_tokens=usage.output_tokens if usage else None,
        )
