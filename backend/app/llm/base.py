"""Provider-neutral LLM interface.

The request carries exactly what the model may see (contract §10.1): a system
instruction, a bounded list of conversation messages, and the JSON schema the
answer must match. It has no field for credentials, so a secret cannot be put
into a request by accident — the API key is a constructor argument of the
concrete provider and never travels with a request.

Every provider failure is translated into one of the `LLMError` subclasses
below, so the rest of the application never handles SDK-specific exceptions and
never sees raw provider error text.
"""

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

Role = Literal["user", "assistant"]


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: Role
    content: str


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """Everything the model receives. Nothing else is sent."""

    system: str
    messages: list[LLMMessage]
    json_schema: dict[str, Any]
    max_output_tokens: int

    def to_dict(self) -> dict[str, Any]:
        """Plain representation, used by tests to prove no secret is present."""
        return {
            "system": self.system,
            "messages": [{"role": m.role, "content": m.content} for m in self.messages],
            "json_schema": self.json_schema,
            "max_output_tokens": self.max_output_tokens,
        }


@dataclass(frozen=True, slots=True)
class LLMResult:
    """The model's raw answer. `text` is untrusted until validated by the caller."""

    text: str
    model: str
    stop_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    """What AKILI needs from any runtime model."""

    name: str
    model: str

    async def complete(self, request: LLMRequest) -> LLMResult:
        """Return the model's structured answer as text, or raise an LLMError."""
        ...


# --------------------------------------------------------------------------- #
# Errors                                                                       #
# --------------------------------------------------------------------------- #


class LLMError(Exception):
    """Base for every provider failure. Messages never contain secrets or raw
    provider payloads — they are safe to log and to store as an error class."""

    error_class: str = "LLM_ERROR"
    retryable: bool = False


class LLMConfigurationError(LLMError):
    """Provider, model, or key is missing or invalid. A deployment problem."""

    error_class = "LLM_NOT_CONFIGURED"


class LLMTimeoutError(LLMError):
    error_class = "LLM_TIMEOUT"
    retryable = True


class LLMRateLimitError(LLMError):
    error_class = "LLM_RATE_LIMITED"
    retryable = True


class LLMConnectionError(LLMError):
    error_class = "LLM_CONNECTION_FAILED"
    retryable = True


class LLMProviderError(LLMError):
    """The provider returned an error status (authentication, server error, ...)."""

    error_class = "LLM_PROVIDER_ERROR"

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LLMResponseError(LLMError):
    """The provider answered, but not with something usable: empty content,
    truncated output, a refusal, or an unexpected shape."""

    error_class = "LLM_BAD_RESPONSE"
