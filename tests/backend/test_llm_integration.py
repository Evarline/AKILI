"""Opt-in check against the real provider. Not part of the default suite.

Runs only when AKILI_LLM_INTEGRATION=1 is set *and* LLM_API_KEY / LLM_MODEL are
configured. Costs money and needs the network, so it is never on by default.

    AKILI_LLM_INTEGRATION=1 pytest tests/backend/test_llm_integration.py
"""

import asyncio
import os

import pytest

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.schemas import Intent, raw_interpretation_json_schema
from app.agent.service import parse_interpretation
from app.core.config import get_settings
from app.llm.base import LLMMessage, LLMRequest
from app.llm.factory import get_llm_provider

settings = get_settings()

pytestmark = pytest.mark.skipif(
    os.environ.get("AKILI_LLM_INTEGRATION") != "1"
    or settings.llm_api_key is None
    or not settings.llm_model,
    reason="set AKILI_LLM_INTEGRATION=1 and configure LLM_API_KEY / LLM_MODEL",
)


def test_real_model_returns_a_contract_valid_interpretation() -> None:
    provider = get_llm_provider()
    request = LLMRequest(
        system=SYSTEM_PROMPT,
        messages=[LLMMessage(role="user", content="I have $20 and want to buy some Bitcoin.")],
        json_schema=raw_interpretation_json_schema(),
        max_output_tokens=settings.llm_max_output_tokens,
    )

    result = asyncio.run(provider.complete(request))
    interpretation = parse_interpretation(result.text)

    assert interpretation.intent is Intent.BUY_SPOT
    assert interpretation.parameters is not None
    assert interpretation.parameters.asset in {"BTC", "BITCOIN"}
    assert str(interpretation.parameters.quote_amount) in {"20", "20.0", "20.00"}
