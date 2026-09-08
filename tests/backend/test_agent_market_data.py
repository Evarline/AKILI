"""The whole market-data path through the chat endpoint, with both edges faked.

The LLM provider and the market-data provider are both replaced at the
application boundary, so these tests prove AKILI's own orchestration — that the
model's *request* becomes a backend call, that the facts come back to the model,
and that the answer the user gets is the fact-grounded one — with no network, no
key, and no live Binance call.

They need PostgreSQL (TEST_DATABASE_URL) and are skipped without it. Identity is
overridden to one seeded user, as in test_chat.py.
"""

import asyncio
import json
from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.agent.capabilities import KLINES_LIMIT
from app.agent.service import RUN_COMPLETED, RUN_FAILED
from app.auth.dependencies import get_current_user
from app.auth.models import CurrentUser
from app.binance.exceptions import BinanceAPIError, InvalidSymbolError, NetworkTimeoutError
from app.binance.providers.factory import get_market_data_provider
from app.core.config import get_settings
from app.db.base import Base
from app.db.models import USER_ORIGIN_DEVELOPMENT, AgentRun, Message, User
from app.db.session import get_db
from app.llm.base import LLMRequest, LLMResult
from app.llm.factory import get_llm_provider
from app.main import app

from tests.backend.test_market_data_capability import KLINE, TICKER, FakeMarketDataProvider

settings = get_settings()

pytestmark = pytest.mark.skipif(
    settings.test_database_url is None, reason="TEST_DATABASE_URL is not configured"
)


class FakeProvider:
    """Returns queued texts (or raises queued exceptions) and records every request."""

    name = "fake"
    model = "fake-model"

    def __init__(self) -> None:
        self.queue: list[str | Exception] = []
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResult:
        self.requests.append(request)
        item = self.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return LLMResult(text=item, model=self.model, input_tokens=11, output_tokens=7)


@pytest.fixture(scope="module")
def test_sessionmaker() -> Iterator[async_sessionmaker]:
    engine = create_async_engine(str(settings.test_database_url), poolclass=NullPool)

    async def create() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async def drop() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(create())
    yield async_sessionmaker(engine, expire_on_commit=False)
    asyncio.run(drop())


@pytest.fixture(scope="module")
def test_user(test_sessionmaker: async_sessionmaker) -> CurrentUser:
    user_id = uuid4()

    async def create() -> None:
        async with test_sessionmaker() as session:
            session.add(User(id=user_id, origin=USER_ORIGIN_DEVELOPMENT))
            await session.commit()

    asyncio.run(create())
    return CurrentUser(id=user_id)


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def market_data() -> FakeMarketDataProvider:
    return FakeMarketDataProvider()


@pytest.fixture
def client(
    test_sessionmaker: async_sessionmaker,
    provider: FakeProvider,
    market_data: FakeMarketDataProvider,
    test_user: CurrentUser,
) -> Iterator[TestClient]:
    async def override_get_db():
        async with test_sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_llm_provider] = lambda: provider
    app.dependency_overrides[get_market_data_provider] = lambda: market_data
    app.dependency_overrides[get_current_user] = lambda: test_user
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def db_query(test_sessionmaker: async_sessionmaker, stmt: Any) -> list[Any]:
    async def run() -> list[Any]:
        async with test_sessionmaker() as session:
            return list((await session.execute(stmt)).scalars())

    return asyncio.run(run())


def chat(client: TestClient, message: str):
    return client.post("/api/v1/chat", json={"message": message})


def requests_data(**request: Any) -> str:
    """What the model returns when it asks AKILI to fetch something."""
    return json.dumps(
        {
            "intent": "MARKET_INFORMATION",
            "requires_clarification": False,
            "message": "Let me check that for you.",
            "question": None,
            "parameters": None,
            "market_data_request": request,
        }
    )


def answers(message: str, **fields: Any) -> str:
    """What the model returns once the facts are in front of it."""
    payload: dict[str, Any] = {
        "intent": "MARKET_INFORMATION",
        "requires_clarification": False,
        "message": message,
        "question": None,
        "parameters": None,
    }
    payload.update(fields)
    return json.dumps(payload)


def latest_run(test_sessionmaker: async_sessionmaker) -> AgentRun:
    return db_query(
        test_sessionmaker, select(AgentRun).order_by(AgentRun.started_at.desc()).limit(1)
    )[0]


# --------------------------------------------------------------------------- #
# get_ticker, end to end                                                       #
# --------------------------------------------------------------------------- #


def test_price_question_fetches_a_ticker_and_answers_from_it(
    client: TestClient,
    provider: FakeProvider,
    market_data: FakeMarketDataProvider,
    test_sessionmaker,
) -> None:
    provider.queue.append(requests_data(capability="get_ticker", symbol="btcusdt"))
    provider.queue.append(answers("Bitcoin is about 79,320 USDT, down 1.5% over 24 hours."))

    response = chat(client, "What's Bitcoin trading at?")

    assert response.status_code == 200
    body = response.json()

    # The backend made the call, through the provider, with a normalised symbol.
    assert market_data.ticker_calls == ["BTCUSDT"]
    assert market_data.klines_calls == []

    # The user gets the fact-grounded answer, not the holding line of turn one.
    assert body["response"]["intent"] == "MARKET_INFORMATION"
    assert body["response"]["message"].startswith("Bitcoin is about 79,320")
    assert body["response"]["market_data_request"] is None

    # The facts travel beside the interpretation, marked as Binance's.
    facts = body["market_data"]
    assert facts["capability"] == "get_ticker"
    assert facts["symbol"] == "BTCUSDT"
    assert facts["provenance"] == "BINANCE_FACT"
    assert facts["ticker"]["price"] == str(TICKER.price)
    assert facts["ticker"]["price_change_percent_24h"] == str(TICKER.price_change_percent_24h)
    assert facts["klines"] == []
    assert facts["observed_at"] is not None

    # Two model calls: interpret, then answer with the facts attached.
    assert len(provider.requests) == 2
    interpret, answer = provider.requests
    assert "<akili_market_data>" not in json.dumps(interpret.to_dict())
    assert "market_data_request" in interpret.json_schema["properties"]
    block = answer.messages[-1].content
    assert block.startswith("<akili_market_data>")
    assert f"price: {TICKER.price}" in block
    assert "market_data_request" not in answer.json_schema["properties"]

    run = latest_run(test_sessionmaker)
    assert run.status == RUN_COMPLETED
    assert run.intent == "MARKET_INFORMATION"
    # The stored interpretation is the answer, and holds no market figure of its
    # own beyond the words the model chose.
    assert run.interpretation["message"].startswith("Bitcoin is about 79,320")
    assert run.interpretation["market_data_request"] is None
    # Both calls of the turn are accounted for.
    assert run.input_tokens == 22 and run.output_tokens == 14

    # Exactly one assistant message was written: the answer.
    messages = db_query(
        test_sessionmaker,
        select(Message).where(Message.conversation_id == run.conversation_id),
    )
    assert [(m.role, m.content) for m in messages] == [
        ("user", "What's Bitcoin trading at?"),
        ("assistant", body["response"]["message"]),
    ]


# --------------------------------------------------------------------------- #
# get_klines, end to end                                                       #
# --------------------------------------------------------------------------- #


def test_trend_question_fetches_klines_at_the_requested_interval(
    client: TestClient,
    provider: FakeProvider,
    market_data: FakeMarketDataProvider,
    test_sessionmaker,
) -> None:
    provider.queue.append(
        requests_data(capability="get_klines", symbol="eth/usdt", interval="4h")
    )
    provider.queue.append(answers("Over the last 4-hour candles ETH closed at 80,250 USDT."))

    response = chat(client, "How has Ethereum moved over the last while?")

    assert response.status_code == 200
    assert market_data.klines_calls == [("ETHUSDT", "4h", KLINES_LIMIT)]
    assert market_data.ticker_calls == []

    facts = response.json()["market_data"]
    assert facts["capability"] == "get_klines"
    assert facts["symbol"] == "ETHUSDT"
    assert facts["interval"] == "4h"
    assert facts["ticker"] is None
    assert len(facts["klines"]) == 1
    assert facts["klines"][0]["close_price"] == str(KLINE.close_price)

    block = provider.requests[1].messages[-1].content
    assert "interval: 4h" in block
    assert str(KLINE.close_price) in block

    assert latest_run(test_sessionmaker).status == RUN_COMPLETED


def test_klines_without_an_interval_uses_the_default(
    client: TestClient, provider: FakeProvider, market_data: FakeMarketDataProvider
) -> None:
    provider.queue.append(requests_data(capability="get_klines", symbol="BTCUSDT"))
    provider.queue.append(answers("Bitcoin's last hourly candles closed at 80,250 USDT."))

    assert chat(client, "Is Bitcoin trending up?").status_code == 200
    assert market_data.klines_calls == [("BTCUSDT", "1h", KLINES_LIMIT)]


# --------------------------------------------------------------------------- #
# Nothing is fetched unless the model asked for it                             #
# --------------------------------------------------------------------------- #


def test_a_market_question_that_needs_clarification_fetches_nothing(
    client: TestClient, provider: FakeProvider, market_data: FakeMarketDataProvider
) -> None:
    provider.queue.append(
        json.dumps(
            {
                "intent": "MARKET_INFORMATION",
                "requires_clarification": True,
                "message": "Happy to check a price for you.",
                "question": "Which coin would you like the price of?",
                "parameters": None,
                "market_data_request": None,
            }
        )
    )

    response = chat(client, "What's the price?")

    assert response.status_code == 200
    assert response.json()["response"]["question"].startswith("Which coin")
    assert response.json()["market_data"] is None
    assert market_data.ticker_calls == [] and market_data.klines_calls == []
    assert len(provider.requests) == 1  # no second turn without facts


def test_other_intents_never_reach_the_market_data_provider(
    client: TestClient, provider: FakeProvider, market_data: FakeMarketDataProvider
) -> None:
    provider.queue.append(
        json.dumps(
            {
                "intent": "GENERAL_INFORMATION",
                "requires_clarification": False,
                "message": "A market order buys at the best price available now.",
                "question": None,
                "parameters": None,
                "market_data_request": None,
            }
        )
    )

    response = chat(client, "What is a market order?")

    assert response.status_code == 200
    assert response.json()["market_data"] is None
    assert market_data.ticker_calls == [] and market_data.klines_calls == []


# --------------------------------------------------------------------------- #
# Failures: no data invented, run recorded as failed                           #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_class"),
    [
        (NetworkTimeoutError("no answer"), 503, "NETWORK_TIMEOUT"),
        (BinanceAPIError("bad gateway", status_code=502), 503, "BINANCE_API_ERROR"),
        (InvalidSymbolError("unknown symbol"), 400, "INVALID_SYMBOL"),
    ],
)
def test_a_failed_fetch_fails_the_turn_instead_of_guessing(
    error: Exception,
    expected_status: int,
    expected_class: str,
    client: TestClient,
    provider: FakeProvider,
    market_data: FakeMarketDataProvider,
    test_sessionmaker,
) -> None:
    market_data._error = error
    provider.queue.append(requests_data(capability="get_ticker", symbol="BTCUSDT"))
    provider.queue.append(answers("Bitcoin is about 79,320 USDT."))  # must never be used

    response = chat(client, "What's Bitcoin trading at?")

    assert response.status_code == expected_status
    assert str(error) not in response.text
    assert "79,320" not in response.text
    # The model was never given a chance to answer without data.
    assert len(provider.requests) == 1

    run = latest_run(test_sessionmaker)
    assert run.status == RUN_FAILED
    assert run.error_class == expected_class
    assert run.interpretation is None
    assert run.assistant_message_id is None
    roles = [
        m.role
        for m in db_query(
            test_sessionmaker,
            select(Message).where(Message.conversation_id == run.conversation_id),
        )
    ]
    assert roles == ["user"]


def test_an_unknown_symbol_never_reaches_the_provider(
    client: TestClient,
    provider: FakeProvider,
    market_data: FakeMarketDataProvider,
    test_sessionmaker,
) -> None:
    """A malformed symbol from the model is rejected by the market-data layer's
    own validation, before any call is attempted."""
    provider.queue.append(requests_data(capability="get_ticker", symbol="not a symbol!"))

    response = chat(client, "What's the price of that thing?")

    assert response.status_code == 400
    assert response.json() == {"detail": "AKILI could not look up that market"}
    assert market_data.ticker_calls == []
    assert latest_run(test_sessionmaker).error_class == "INVALID_SYMBOL"


def test_an_answer_asking_for_more_data_is_rejected(
    client: TestClient,
    provider: FakeProvider,
    market_data: FakeMarketDataProvider,
    test_sessionmaker,
) -> None:
    provider.queue.append(requests_data(capability="get_ticker", symbol="BTCUSDT"))
    provider.queue.append(
        answers(
            "Let me also check the candles.",
            market_data_request={"capability": "get_klines", "symbol": "BTCUSDT"},
        )
    )

    response = chat(client, "What's Bitcoin trading at?")

    assert response.status_code == 502
    assert response.json() == {"detail": "The assistant returned an unusable response"}
    # One fetch happened, and no second one was made off the back of the answer.
    assert market_data.ticker_calls == ["BTCUSDT"]
    assert market_data.klines_calls == []
    run = latest_run(test_sessionmaker)
    assert run.status == RUN_FAILED
    assert run.error_class == "INVALID_MODEL_OUTPUT"


def test_no_secret_travels_with_either_turn(
    client: TestClient, provider: FakeProvider, market_data: FakeMarketDataProvider
) -> None:
    provider.queue.append(requests_data(capability="get_ticker", symbol="BTCUSDT"))
    provider.queue.append(answers("Bitcoin is about 79,320 USDT."))

    assert chat(client, "What's Bitcoin trading at?").status_code == 200

    db_password = str(settings.database_url).split("@")[0].rsplit(":", 1)[1]
    for request in provider.requests:
        sent = json.dumps(request.to_dict())
        assert db_password not in sent
        assert str(settings.database_url) not in sent
        assert set(request.to_dict()) == {
            "system",
            "messages",
            "json_schema",
            "max_output_tokens",
        }
