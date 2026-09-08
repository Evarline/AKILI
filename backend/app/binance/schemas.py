"""Market-data domain types: what AKILI's consumers receive from any provider.

Prices, changes, and volumes are `Decimal`, following the agent contract (§3):
Binance transmits them as strings precisely so that no float rounding occurs,
and AKILI keeps that exactness end to end. Times are timezone-aware UTC
datetimes, like every timestamp in the database. Models are frozen and reject
unknown fields, so a provider cannot leak raw fields through by accident.
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.binance.exceptions import InvalidIntervalError, InvalidSymbolError

# Candle intervals the beginner-focused MVP exposes. Deliberately small.
Interval = Literal["1h", "4h", "1d"]
SUPPORTED_INTERVALS: tuple[Interval, ...] = ("1h", "4h", "1d")

# A Binance Spot symbol after normalisation: e.g. BTCUSDT, ETHBTC, 1INCHUSDT.
_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{5,20}$")
_SYMBOL_SEPARATORS = re.compile(r"[\s/_\-:]+")


def normalize_symbol(raw: str) -> str:
    """Turn user-shaped input ("btc/usdt", " BTC-USDT ", "btcusdt") into "BTCUSDT".

    Raises:
        InvalidSymbolError: the input is empty or not symbol-shaped. Whether a
            well-formed symbol actually exists is for the provider to find out.
    """
    if not isinstance(raw, str):
        raise InvalidSymbolError("symbol must be a string")
    symbol = _SYMBOL_SEPARATORS.sub("", raw.strip()).upper()
    if not _SYMBOL_PATTERN.fullmatch(symbol):
        raise InvalidSymbolError(f"not a valid trading symbol: {raw.strip()[:32]!r}")
    return symbol


def validate_interval(interval: str) -> Interval:
    """Accept only the MVP intervals, exactly as spelled."""
    if interval not in SUPPORTED_INTERVALS:
        raise InvalidIntervalError(
            f"unsupported interval {interval!r}; supported: {', '.join(SUPPORTED_INTERVALS)}"
        )
    return interval  # type: ignore[return-value]


class _MarketDataModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Ticker(_MarketDataModel):
    """A 24-hour rolling snapshot for one Spot symbol."""

    symbol: str
    price: Decimal = Field(description="Last traded price, in the quote asset.")
    price_change_24h: Decimal = Field(description="Absolute price change over 24h.")
    price_change_percent_24h: Decimal = Field(description="Price change over 24h, in percent.")
    high_24h: Decimal
    low_24h: Decimal
    volume_24h: Decimal = Field(description="Traded volume over 24h, in the base asset.")


class Kline(_MarketDataModel):
    """One candlestick."""

    open_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal = Field(description="Traded volume in the candle, in the base asset.")
    close_time: datetime

    @field_validator("open_time", "close_time")
    @classmethod
    def _must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("kline times must be timezone-aware")
        return value


class AccountBalance(_MarketDataModel):
    """One real Spot balance returned by the authenticated account endpoint."""

    asset: str
    free: Decimal
    locked: Decimal


class SpotAccount(_MarketDataModel):
    """Safe subset of Binance Spot account data exposed by AKILI."""

    account_type: str
    can_trade: bool
    balances: tuple[AccountBalance, ...]
