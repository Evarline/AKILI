"""Anthropic provider adapter, tested against a stand-in SDK client.

No network and no key: the client object is replaced by a fake whose
`messages.create` records the call and returns or raises what the test says.
"""

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2
import pytest

from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import (
    LLMConfigurationError,
    LLMConnectionError,
    LLMMessage,
    LLMProviderError,
    LLMRateLimitError,
    LLMRequest,
    LLMResponseError,
    LLMTimeoutError,
)

API_KEY = "sk-ant-TEST-KEY-do-not-send-1234"
REQUEST = LLMRequest(
    system="You are AKILI.",
    messages=[LLMMessage(role="user", content="What is Bitcoin?")],
    json_schema={"type": "object", "properties": {}, "additionalProperties": False},
    max_output_tokens=512,
)


class FakeMessages:
    def __init__(self, outcome: Any) -> None:
        self.outcome = outcome
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def make_provider(outcome: Any) -> tuple[AnthropicProvider, FakeMessages]:
    messages = FakeMessages(outcome)
    client = SimpleNamespace(messages=messages)
    provider = AnthropicProvider(api_key=API_KEY, model="some-model", timeout_seconds=5, client=client)  # type: ignore[arg-type]
    return provider, messages


def sdk_response(text: str | None = "{}", stop_reason: str = "end_turn") -> Any:
    content = [] if text is None else [SimpleNamespace(type="text", text=text)]
    return SimpleNamespace(
        content=content,
        stop_reason=stop_reason,
        model="some-model-2026",
        usage=SimpleNamespace(input_tokens=42, output_tokens=9),
    )


def http_request() -> httpx2.Request:
    return httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def http_response(status: int) -> httpx2.Response:
    return httpx2.Response(status, request=http_request())


# --------------------------------------------------------------------------- #


def test_request_is_sent_as_structured_output_without_the_key() -> None:
    provider, messages = make_provider(sdk_response('{"intent": "GENERAL_INFORMATION"}'))

    result = asyncio.run(provider.complete(REQUEST))

    call = messages.calls[0]
    assert call["model"] == "some-model"
    assert call["max_tokens"] == 512
    assert call["system"] == "You are AKILI."
    assert call["messages"] == [{"role": "user", "content": "What is Bitcoin?"}]
    assert call["output_config"] == {"format": {"type": "json_schema", "schema": REQUEST.json_schema}}
    # The key belongs to the client, never to a request.
    assert API_KEY not in json.dumps(call, default=str)
    assert result.text == '{"intent": "GENERAL_INFORMATION"}'
    assert result.model == "some-model-2026"
    assert (result.input_tokens, result.output_tokens) == (42, 9)


@pytest.mark.parametrize(
    ("sdk_error", "expected"),
    [
        (anthropic.APITimeoutError(request=http_request()), LLMTimeoutError),
        (anthropic.APIConnectionError(request=http_request()), LLMConnectionError),
        (anthropic.RateLimitError("429", response=http_response(429), body=None), LLMRateLimitError),
        (anthropic.AuthenticationError("401", response=http_response(401), body=None), LLMConfigurationError),
        (anthropic.PermissionDeniedError("403", response=http_response(403), body=None), LLMConfigurationError),
        (anthropic.InternalServerError("500", response=http_response(500), body=None), LLMProviderError),
        (anthropic.BadRequestError("400", response=http_response(400), body=None), LLMProviderError),
    ],
)
def test_sdk_errors_map_to_akili_errors(sdk_error: Exception, expected: type[Exception]) -> None:
    provider, _ = make_provider(sdk_error)

    with pytest.raises(expected) as info:
        asyncio.run(provider.complete(REQUEST))

    # Our error text names the failure class, never the provider's raw message.
    assert API_KEY not in str(info.value)
    if isinstance(info.value, LLMProviderError):
        assert info.value.status_code in (400, 500)


@pytest.mark.parametrize(
    "response",
    [
        pytest.param(sdk_response(stop_reason="refusal"), id="refusal"),
        pytest.param(sdk_response(stop_reason="max_tokens"), id="truncated"),
        pytest.param(sdk_response(text=None), id="no-text-block"),
        pytest.param(sdk_response(text="   "), id="blank-text"),
    ],
)
def test_unusable_responses_raise_response_error(response: Any) -> None:
    provider, _ = make_provider(response)

    with pytest.raises(LLMResponseError):
        asyncio.run(provider.complete(REQUEST))
