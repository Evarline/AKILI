"""AKILI depends on the MarketDataProvider abstraction; Binance REST is currently one
implementation. A future MCP provider can implement the same contract without
changing AKILI's market-data consumers.

The contract is deliberately small — the two reads a beginner-focused Spot MVP
needs — and provider-agnostic: it speaks in symbols, intervals, and the domain
types in `app.binance.schemas`, never in URLs, headers, tool names, or raw
payloads. Implementations raise only `app.binance.exceptions.MarketDataError`
subclasses, so a consumer written against this protocol needs no knowledge of
which provider is behind it.
"""

from typing import Protocol, runtime_checkable

from app.binance.schemas import Interval, Kline, SpotAccount, Ticker


@runtime_checkable
class MarketDataProvider(Protocol):
    """Read-only market data for Binance Spot symbols."""

    name: str

    async def get_ticker(self, symbol: str) -> Ticker:
        """The 24h ticker for one symbol.

        Args:
            symbol: user-shaped input; implementations normalise it
                (``"btc/usdt"`` → ``"BTCUSDT"``).

        Raises:
            InvalidSymbolError, BinanceAPIError, NetworkTimeoutError, MarketDataError
        """
        ...

    async def get_klines(self, symbol: str, interval: Interval = "1h", limit: int = 100) -> list[Kline]:
        """Up to ``limit`` most recent candles for one symbol, oldest first.

        Raises:
            InvalidSymbolError, InvalidIntervalError, BinanceAPIError,
            NetworkTimeoutError, MarketDataError
        """
        ...

    async def get_account(self) -> SpotAccount:
        """The authenticated Spot account and its balances."""
        ...
