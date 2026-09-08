"""The structured contract between the runtime model and AKILI.

Two schemas, deliberately separate, following docs/01-AGENT-CONTRACT.md §3:

- `RawInterpretation` is what the model is asked to produce. Plain JSON types
  only, so it can be expressed as a strict JSON schema for the provider. Every
  value in it is MODEL INTERPRETATION: untrusted and advisory.
- `Interpretation` is what AKILI accepts after validating and normalising the
  raw output — the BACKEND-VALIDATED form. Monetary values become Decimals, the
  intent set is closed, and the cross-field rules of §5 are enforced.

Promotion from raw to validated happens in exactly one place,
`Interpretation._from_turn`, and it fails loudly rather than repairing anything
by guesswork (§10.4).

Two turns share these types. In the UNDERSTAND turn the model may *request* a
read-only market-data call (`market_data_request`) — a request is not a fetch:
AKILI validates it and makes the call itself (§9.2). In the fact-grounded
EXPLAIN turn the model answers from data AKILI already fetched, so `RawAnswer`
has no request field at all and the model cannot ask for another call.

No field here ever carries a Binance fact. Facts live in
`app.agent.capabilities.MarketDataFacts`, with BINANCE_FACT provenance and the
moment they were observed; nothing the model returns is a fact about the market,
the user's account, or Binance's rules.
"""

from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.binance.schemas import Interval


class Intent(StrEnum):
    """The closed intent set from the agent contract §5."""

    GENERAL_INFORMATION = "GENERAL_INFORMATION"
    MARKET_INFORMATION = "MARKET_INFORMATION"
    ACCOUNT_INFORMATION = "ACCOUNT_INFORMATION"
    BUY_SPOT = "BUY_SPOT"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    UNSUPPORTED_ACTION = "UNSUPPORTED_ACTION"


class Provenance(StrEnum):
    """Trust class of a value (contract §3)."""

    USER_INPUT = "USER_INPUT"
    MODEL_INTERPRETATION = "MODEL_INTERPRETATION"
    APPLICATION_GENERATED = "APPLICATION_GENERATED"
    BINANCE_FACT = "BINANCE_FACT"


# --------------------------------------------------------------------------- #
# What the model is asked to return                                            #
# --------------------------------------------------------------------------- #


Capability = Literal["get_ticker", "get_klines"]
"""The read-only market-data calls the model may ask AKILI to make (§9.1, T-R1).

Deliberately the two the market-data layer already provides. Nothing else is
requestable: there is no account, order, or write capability to name.
"""


class RawMarketDataRequest(BaseModel):
    """The market-data call the model is asking AKILI to make.

    A request, not an action. Every value in it is MODEL INTERPRETATION and is
    re-validated by the capability layer, with the market-data layer's own
    `normalize_symbol` / `validate_interval`, before any call is made.
    """

    model_config = ConfigDict(extra="forbid")

    capability: Capability = Field(
        description="Which read-only call AKILI should make: 'get_ticker' for the "
        "current price and 24-hour snapshot, 'get_klines' for recent candles.",
    )
    symbol: str = Field(
        description="The Binance Spot trading symbol, e.g. 'BTCUSDT'. When the user "
        "named only an asset, pair it with USDT. Never a symbol for an asset the "
        "user did not name.",
    )
    interval: Interval | None = Field(
        default=None,
        description="Only for get_klines: '1h', '4h', or '1d'. Null for get_ticker; "
        "null for get_klines means the default 1h.",
    )


class RawBuySpotParameters(BaseModel):
    """Trade slots as the model extracted them from the user's words.

    The model reports what the user *said*, not what it *concluded*: the asset as
    named ("BTC", "Bitcoin"), the amount as a decimal string, and the currency the
    user expressed the amount in. It does not resolve a trading pair or convert
    currencies — those are backend decisions against Binance facts in a later
    phase.
    """

    model_config = ConfigDict(extra="forbid")

    asset: str | None = Field(
        default=None,
        description="The asset the user wants to buy, as they named it (e.g. 'BTC', "
        "'Bitcoin'). Null if not stated. Do not guess.",
    )
    quote_amount: str | None = Field(
        default=None,
        description="The amount the user wants to spend, as a plain decimal string "
        "such as '20' or '12.50'. Null if not stated. Never estimate.",
    )
    quote_currency: str | None = Field(
        default=None,
        description="The currency the user expressed the amount in, as stated "
        "(e.g. 'USD', 'USDT', 'EUR'). Null if not stated. Do not convert.",
    )


class _RawTurn(BaseModel):
    """What every model turn must return. Strict: unknown keys are rejected."""

    model_config = ConfigDict(extra="forbid")

    intent: Intent = Field(description="Exactly one intent from the closed set.")
    requires_clarification: bool = Field(
        description="True when required information is missing or ambiguous and "
        "AKILI must ask before anything else can happen."
    )
    message: str = Field(
        description="What AKILI says to the user: plain, brief, beginner-friendly. "
        "Never claims an action was performed and never states market or account "
        "figures.",
    )
    question: str | None = Field(
        default=None,
        description="When requires_clarification is true, the single focused "
        "question to ask. Otherwise null.",
    )
    parameters: RawBuySpotParameters | None = Field(
        default=None,
        description="Only for BUY_SPOT: the slots extracted so far. Null for every "
        "other intent.",
    )


class RawInterpretation(_RawTurn):
    """The UNDERSTAND turn: an interpretation that may request market data."""

    market_data_request: RawMarketDataRequest | None = Field(
        default=None,
        description="Only for MARKET_INFORMATION: the read-only market-data call "
        "AKILI should make before answering. Null for every other intent, and null "
        "when asking a clarifying question.",
    )


class RawAnswer(_RawTurn):
    """The EXPLAIN turn, answered from market data AKILI already fetched.

    Identical to `RawInterpretation` minus `market_data_request`: the field does
    not exist in this schema, so a second fetch cannot be requested — and, since
    unknown keys are rejected, asking for one anyway fails validation.
    """


def raw_interpretation_json_schema() -> dict[str, Any]:
    """The JSON schema handed to the provider for the UNDERSTAND turn."""
    return RawInterpretation.model_json_schema()


def raw_answer_json_schema() -> dict[str, Any]:
    """The JSON schema handed to the provider for the fact-grounded turn."""
    return RawAnswer.model_json_schema()


# --------------------------------------------------------------------------- #
# What AKILI accepts                                                            #
# --------------------------------------------------------------------------- #

_MAX_MESSAGE_CHARS = 2000
_MAX_SYMBOL_CHARS = 20
_MAX_ASSET_CHARS = 20
_MAX_CURRENCY_CHARS = 10


class MarketDataRequest(BaseModel):
    """A market-data call AKILI has accepted as well-formed enough to consider.

    Still MODEL INTERPRETATION in origin: the symbol is only shape-checked here
    (trimmed and upper-cased), and the capability layer runs it through
    `normalize_symbol` before Binance is asked whether it exists at all.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    capability: Capability
    symbol: str = Field(min_length=1, max_length=_MAX_SYMBOL_CHARS)
    interval: Interval | None = None


class BuySpotParameters(BaseModel):
    """Validated, normalised trade slots. Still MODEL INTERPRETATION in origin."""

    model_config = ConfigDict(extra="forbid")

    asset: str | None = Field(default=None, max_length=_MAX_ASSET_CHARS)
    quote_amount: Decimal | None = Field(default=None, gt=Decimal("0"))
    quote_currency: str | None = Field(default=None, max_length=_MAX_CURRENCY_CHARS)

    @property
    def is_complete(self) -> bool:
        return self.asset is not None and self.quote_amount is not None


class Interpretation(BaseModel):
    """A model interpretation that passed AKILI's contract checks (§5, §10.4)."""

    model_config = ConfigDict(extra="forbid")

    intent: Intent
    requires_clarification: bool
    message: str = Field(min_length=1, max_length=_MAX_MESSAGE_CHARS)
    question: str | None = Field(default=None, max_length=_MAX_MESSAGE_CHARS)
    parameters: BuySpotParameters | None = None
    market_data_request: MarketDataRequest | None = None
    provenance: Literal[Provenance.MODEL_INTERPRETATION] = Provenance.MODEL_INTERPRETATION

    @model_validator(mode="after")
    def _enforce_contract(self) -> Self:
        if self.intent is Intent.CLARIFICATION_REQUIRED and not self.requires_clarification:
            raise ValueError("CLARIFICATION_REQUIRED must set requires_clarification")
        if self.requires_clarification and not (self.question and self.question.strip()):
            raise ValueError("requires_clarification without a question")
        if not self.requires_clarification and self.question is not None:
            raise ValueError("question given but requires_clarification is false")
        if self.intent is Intent.UNSUPPORTED_ACTION and self.requires_clarification:
            raise ValueError("UNSUPPORTED_ACTION cannot require clarification")

        if self.intent is Intent.BUY_SPOT:
            if not self.requires_clarification and (
                self.parameters is None or not self.parameters.is_complete
            ):
                raise ValueError("complete BUY_SPOT needs asset and quote_amount")
        elif self.parameters is not None:
            raise ValueError("parameters are only allowed for BUY_SPOT")

        if self.market_data_request is not None:
            if self.intent is not Intent.MARKET_INFORMATION:
                raise ValueError("market_data_request is only allowed for MARKET_INFORMATION")
            if self.requires_clarification:
                raise ValueError("a clarifying question cannot also request market data")
            if self.market_data_request.capability == "get_ticker" and (
                self.market_data_request.interval is not None
            ):
                raise ValueError("interval is only allowed for get_klines")
        return self

    @classmethod
    def from_raw(cls, raw: RawInterpretation) -> Self:
        """Promote an UNDERSTAND turn, or raise ValueError.

        A market question that is not asking the user anything must name the
        call AKILI should make: otherwise the model would be answering about
        the market with no market data, which is exactly what it may not do.
        """
        try:
            request = (
                None
                if raw.market_data_request is None
                else MarketDataRequest(
                    capability=raw.market_data_request.capability,
                    symbol=_normalise_token(raw.market_data_request.symbol) or "",
                    interval=raw.market_data_request.interval,
                )
            )
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc

        interpretation = cls._from_turn(raw, market_data_request=request)
        if (
            interpretation.intent is Intent.MARKET_INFORMATION
            and not interpretation.requires_clarification
            and interpretation.market_data_request is None
        ):
            raise ValueError("MARKET_INFORMATION must name the market-data call to make")
        return interpretation

    @classmethod
    def from_raw_answer(cls, raw: RawAnswer) -> Self:
        """Promote the fact-grounded turn, or raise ValueError.

        The turn exists only because market data was fetched for a market
        question, so it must still be one: an answer that wandered to another
        intent is rejected rather than recorded as if it were the answer.
        """
        interpretation = cls._from_turn(raw, market_data_request=None)
        if interpretation.intent is not Intent.MARKET_INFORMATION:
            raise ValueError("a market-data answer must stay MARKET_INFORMATION")
        return interpretation

    @classmethod
    def _from_turn(
        cls, raw: _RawTurn, *, market_data_request: MarketDataRequest | None
    ) -> Self:
        """The shared promotion: normalise, then enforce the contract."""
        parameters: BuySpotParameters | None = None
        if raw.parameters is not None:
            parameters = BuySpotParameters(
                asset=_normalise_token(raw.parameters.asset),
                quote_amount=_parse_decimal(raw.parameters.quote_amount),
                quote_currency=_normalise_token(raw.parameters.quote_currency),
            )
            if parameters.asset is None and parameters.quote_amount is None and (
                parameters.quote_currency is None
            ):
                parameters = None

        try:
            return cls(
                intent=raw.intent,
                requires_clarification=raw.requires_clarification,
                message=raw.message.strip(),
                question=raw.question.strip() if raw.question else None,
                parameters=parameters,
                market_data_request=market_data_request,
            )
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc


def _normalise_token(value: str | None) -> str | None:
    """Trim and upper-case a ticker-like token; empty becomes None."""
    if value is None:
        return None
    value = value.strip().upper()
    return value or None


def _parse_decimal(value: str | None) -> Decimal | None:
    """Parse a decimal string strictly. Floats are never involved (§3)."""
    if value is None or not value.strip():
        return None
    try:
        amount = Decimal(value.strip().replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError(f"quote_amount is not a decimal: {value!r}") from exc
    if not amount.is_finite():
        raise ValueError("quote_amount must be finite")
    return amount
