"""Select and build the configured LLM provider."""

from functools import lru_cache

from app.core.config import get_settings
from app.llm.base import LLMConfigurationError, LLMProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    """The process-wide provider, built from settings on first use.

    Also the FastAPI dependency for routes that talk to the model; tests replace
    it through `app.dependency_overrides`. Raises LLMConfigurationError — which
    the app answers with a 503 — rather than falling back to anything.
    """
    settings = get_settings()

    if settings.llm_provider == "anthropic":
        if settings.llm_api_key is None:
            raise LLMConfigurationError("LLM_API_KEY is not configured")
        if not settings.llm_model:
            raise LLMConfigurationError("LLM_MODEL is not configured")

        from app.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(
            api_key=settings.llm_api_key.get_secret_value(),
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    if settings.llm_provider == "google":
        if settings.llm_api_key is None:
            raise LLMConfigurationError("LLM_API_KEY is not configured")
        if not settings.llm_model:
            raise LLMConfigurationError("LLM_MODEL is not configured")

        from app.llm.google_provider import GoogleProvider

        return GoogleProvider(
            api_key=settings.llm_api_key.get_secret_value(),
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    raise LLMConfigurationError(f"unsupported LLM_PROVIDER: {settings.llm_provider}")
