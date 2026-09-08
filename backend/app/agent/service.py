"""The chat service: one user message in, one validated interpretation out.

Sequence (all persistence is in PostgreSQL):

1. Find or create the conversation — always scoped to the calling user. A
   conversation owned by someone else is indistinguishable from one that does
   not exist (contract INV-11 applied to conversations).
2. Store the user message (USER INPUT).
3. Open an agent run in status RUNNING and commit, so the attempt is on record
   even if the process dies mid-call.
4. Build the model request from a bounded window of this conversation only.
5. Call the provider. Validate its text against the contract.
6. If the interpretation requests market data, run that one read-only call
   through the capability layer (RESEARCHING), then call the provider a second
   time with the facts attached, and validate that answer too. The model asks;
   AKILI calls Binance. The model never does.
7. On success: store the assistant message, mark the run COMPLETED with the
   validated interpretation and the token counts of every call the turn made.
   On failure — provider, contract, or market data — mark the run FAILED with an
   error class and re-raise. Nothing is turned into a fake success, and a failed
   market-data read is never replaced by an estimate (contract INV-16).

The service never decides anything financial. It produces an interpretation, and
market facts where a market question needed them, for later phases to plan,
validate, and seek approval on.
"""

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypeVar
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.capabilities import MarketDataFacts, invoke_market_data
from app.agent.prompts import MARKET_ANSWER_SYSTEM_PROMPT, SYSTEM_PROMPT
from app.agent.schemas import (
    Interpretation,
    RawAnswer,
    RawInterpretation,
    raw_answer_json_schema,
    raw_interpretation_json_schema,
)
from app.auth.models import CurrentUser
from app.binance.exceptions import MarketDataError
from app.binance.providers.base import MarketDataProvider
from app.core.config import Settings, get_settings
from app.db.models import AgentRun, Conversation, Message
from app.llm.base import LLMError, LLMMessage, LLMProvider, LLMRequest

logger = logging.getLogger(__name__)

_RawTurnT = TypeVar("_RawTurnT", RawInterpretation, RawAnswer)

RUN_RUNNING = "RUNNING"
RUN_COMPLETED = "COMPLETED"
RUN_FAILED = "FAILED"


class ConversationNotFoundError(Exception):
    """No conversation with this id is visible to the calling user.

    Raised both when the id does not exist and when it belongs to another user;
    the two cases are deliberately not distinguishable from outside.
    """


class InvalidModelOutputError(Exception):
    """The model answered, but not within the contract. Treated as a failed run."""

    error_class = "INVALID_MODEL_OUTPUT"


@dataclass(frozen=True, slots=True)
class ChatOutcome:
    conversation_id: UUID
    agent_run_id: UUID
    interpretation: Interpretation
    # The facts a market question was answered from, when one was: BINANCE
    # FACT, kept separate from the interpretation so the two trust classes are
    # never merged into one blob.
    market_data: MarketDataFacts | None = None


async def handle_chat(
    session: AsyncSession,
    provider: LLMProvider,
    market_data: MarketDataProvider,
    *,
    user: CurrentUser,
    message: str,
    conversation_id: UUID | None,
) -> ChatOutcome:
    settings = get_settings()
    conversation = await _get_or_create_conversation(session, user.id, conversation_id)

    user_message = Message(conversation_id=conversation.id, role="user", content=message)
    session.add(user_message)
    await session.flush()

    run = AgentRun(
        conversation_id=conversation.id,
        user_message_id=user_message.id,
        status=RUN_RUNNING,
        provider=provider.name,
        model=provider.model,
    )
    session.add(run)
    await session.commit()

    history = await _recent_messages(session, conversation.id, settings.agent_history_messages)
    request = build_request(history, settings)

    facts: MarketDataFacts | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    try:
        result = await provider.complete(request)
        interpretation = parse_interpretation(result.text)
        input_tokens, output_tokens = result.input_tokens, result.output_tokens

        if interpretation.market_data_request is not None:
            # RESEARCHING. The model asked for exactly one read-only call; the
            # capability layer validates it and makes it. Then the model answers
            # from the facts, with no way to ask for more.
            facts = await invoke_market_data(market_data, interpretation.market_data_request)
            answer = await provider.complete(build_answer_request(history, facts, settings))
            interpretation = parse_answer(answer.text)
            input_tokens = _add_tokens(input_tokens, answer.input_tokens)
            output_tokens = _add_tokens(output_tokens, answer.output_tokens)
    except (LLMError, InvalidModelOutputError, MarketDataError) as exc:
        run.status = RUN_FAILED
        run.error_class = exc.error_class
        run.completed_at = datetime.now(UTC)
        await session.commit()
        logger.info("agent run %s failed: %s", run.id, exc.error_class)
        raise

    assistant_message = Message(
        conversation_id=conversation.id, role="assistant", content=interpretation.message
    )
    session.add(assistant_message)
    await session.flush()

    run.status = RUN_COMPLETED
    run.intent = interpretation.intent.value
    run.interpretation = interpretation.model_dump(mode="json")
    run.input_tokens = input_tokens
    run.output_tokens = output_tokens
    run.assistant_message_id = assistant_message.id
    run.completed_at = datetime.now(UTC)
    await session.commit()

    logger.info(
        "agent run %s completed: intent=%s capability=%s",
        run.id,
        run.intent,
        facts.capability if facts else None,
    )
    return ChatOutcome(
        conversation_id=conversation.id,
        agent_run_id=run.id,
        interpretation=interpretation,
        market_data=facts,
    )


def build_request(history: list[Message], settings: Settings) -> LLMRequest:
    """Assemble exactly what the model may see in the UNDERSTAND turn (§10.1).

    A static system instruction plus the most recent messages of this one
    conversation. No other conversations, no settings, no credentials, and no
    Binance data: nothing has been fetched at this point, and the system prompt
    says so.
    """
    return LLMRequest(
        system=SYSTEM_PROMPT,
        messages=[LLMMessage(role=m.role, content=m.content) for m in history],  # type: ignore[arg-type]
        json_schema=raw_interpretation_json_schema(),
        max_output_tokens=settings.llm_max_output_tokens,
    )


def build_answer_request(
    history: list[Message], facts: MarketDataFacts, settings: Settings
) -> LLMRequest:
    """The fact-grounded turn: the same conversation plus what AKILI fetched.

    The facts travel as one extra, clearly delimited message, because the
    provider interface has a single content channel and no place for a
    credential or a side channel. Still no secrets, and still only this user's
    conversation. The schema for this turn has no request field, so the answer
    cannot ask for another call.
    """
    messages = [LLMMessage(role=m.role, content=m.content) for m in history]  # type: ignore[arg-type]
    messages.append(LLMMessage(role="user", content=facts.as_context_block()))
    return LLMRequest(
        system=MARKET_ANSWER_SYSTEM_PROMPT,
        messages=messages,
        json_schema=raw_answer_json_schema(),
        max_output_tokens=settings.llm_max_output_tokens,
    )


def parse_interpretation(text: str) -> Interpretation:
    """Promote the UNDERSTAND turn's untrusted text, or fail."""
    raw = _load(text, RawInterpretation)
    try:
        return Interpretation.from_raw(raw)
    except ValueError as exc:
        raise InvalidModelOutputError("model output violates the contract") from exc


def parse_answer(text: str) -> Interpretation:
    """Promote the fact-grounded turn's untrusted text, or fail.

    Same gates. The answer schema has no market-data request field, so a model
    that asks for another fetch here is rejected by the schema gate rather than
    quietly having the request dropped.
    """
    raw = _load(text, RawAnswer)
    try:
        return Interpretation.from_raw_answer(raw)
    except ValueError as exc:
        raise InvalidModelOutputError("model output violates the contract") from exc


def _load(text: str, model: type[_RawTurnT]) -> _RawTurnT:
    """The first two gates, rejecting rather than repairing (contract §10.4):
    JSON syntax, then the strict raw schema (unknown keys fail)."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidModelOutputError("model output is not valid JSON") from exc
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise InvalidModelOutputError("model output does not match the schema") from exc


def _add_tokens(first: int | None, second: int | None) -> int | None:
    """Sum the token counts of the calls a turn made; None only if both are."""
    if first is None:
        return second
    if second is None:
        return first
    return first + second


async def _get_or_create_conversation(
    session: AsyncSession, user_id: UUID, conversation_id: UUID | None
) -> Conversation:
    """A new conversation owned by `user_id`, or an existing one **of theirs**.

    Ownership is part of the query, not a check after the load: there is no
    code path that holds another user's conversation object, even briefly.
    """
    if conversation_id is None:
        conversation = Conversation(user_id=user_id)
        session.add(conversation)
        await session.flush()
        return conversation
    stmt = select(Conversation).where(
        Conversation.id == conversation_id, Conversation.user_id == user_id
    )
    conversation = (await session.execute(stmt)).scalar_one_or_none()
    if conversation is None:
        raise ConversationNotFoundError(str(conversation_id))
    return conversation


async def _recent_messages(
    session: AsyncSession, conversation_id: UUID, limit: int
) -> list[Message]:
    """The last `limit` messages of one conversation, oldest first.

    The window always starts at a user turn: a leading assistant message left
    over from cutting the window is dropped, because providers require the
    first message to be the user's and a reply without its question is noise.
    """
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    window = list(reversed(list((await session.execute(stmt)).scalars())))
    while window and window[0].role != "user":
        window.pop(0)
    return window
