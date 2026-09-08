"""BinanceRESTProvider: MarketDataProvider over Binance's PUBLIC Spot REST endpoints.

Only two unauthenticated, read-only endpoints are used:

- ``GET /api/v3/ticker/24hr?symbol=…``  → `Ticker`
- ``GET /api/v3/klines?symbol=…&interval=…&limit=…`` → `list[Kline]`

No API key, no secret, no signed request, no account or order endpoint. This
module is the only place in AKILI that knows Binance's REST URL layout, field
names, and array positions; everything it returns is a domain type, and every
failure is a `MarketDataError` subclass. Raw payloads are never logged.
"""

import hashlib
import hmac
import logging
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import httpx2
from pydantic import ValidationError

from app.binance.exceptions import (
    BinanceAPIError,
    BinanceAuthenticationError,
    BinanceRateLimitError,
    BinanceTimestampError,
    InvalidSymbolError,
    MarketDataError,
    NetworkTimeoutError,
)
from app.binance.schemas import (
    AccountBalance,
    Interval,
    Kline,
    SpotAccount,
    Ticker,
    normalize_symbol,
    validate_interval,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.binance.com"
TESTNET_BASE_URL = "https://testnet.binance.vision"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_RECV_WINDOW = 5000
# Binance's own maximum for /api/v3/klines.
MAX_KLINES_LIMIT = 1000

# Binance error codes that mean "that symbol does not exist / is malformed", as
# documented in the Spot API error-code list (-1121 Invalid symbol, -1100
# Illegal characters found in a parameter).
_INVALID_SYMBOL_CODES = frozenset({-1121, -1100})

# /api/v3/klines rows are positional arrays; these are the indexes AKILI reads.
_K_OPEN_TIME, _K_OPEN, _K_HIGH, _K_LOW, _K_CLOSE, _K_VOLUME, _K_CLOSE_TIME = range(7)


class BinanceRESTProvider:
    """Public and authenticated Binance Spot REST data.

    An `httpx2.AsyncClient` may be injected (tests pass one with a mock
    transport; an application may share a pooled one). Without it, a short-lived
    client with the configured timeout is opened per call, so the provider has
    no lifecycle of its own.
    """

    name = "binance-rest"

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        http_client: httpx2.AsyncClient | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
        use_testnet: bool = False,
        recv_window: int = DEFAULT_RECV_WINDOW,
    ) -> None:
        self._base_url = (TESTNET_BASE_URL if use_testnet else base_url).rstrip("/")
        self._timeout = httpx2.Timeout(timeout_seconds)
        self._http_client = http_client
        self._api_key = api_key
        self._api_secret = api_secret
        self._recv_window = recv_window

    # ------------------------------------------------------------------ #
    # MarketDataProvider                                                  #
    # ------------------------------------------------------------------ #

    async def get_ticker(self, symbol: str) -> Ticker:
        normalized = normalize_symbol(symbol)
        payload = await self._get_json("/api/v3/ticker/24hr", {"symbol": normalized}, symbol=normalized)
        return _parse_ticker(payload, symbol=normalized)

    async def get_klines(self, symbol: str, interval: Interval = "1h", limit: int = 100) -> list[Kline]:
        normalized = normalize_symbol(symbol)
        validated_interval = validate_interval(interval)
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_KLINES_LIMIT:
            raise ValueError(f"limit must be an integer between 1 and {MAX_KLINES_LIMIT}")
        payload = await self._get_json(
            "/api/v3/klines",
            {"symbol": normalized, "interval": validated_interval, "limit": limit},
            symbol=normalized,
        )
        if not isinstance(payload, list):
            raise MarketDataError("unexpected klines payload shape")
        return [_parse_kline(row, symbol=normalized) for row in payload]

    async def get_account(self) -> SpotAccount:
        """Fetch the configured account using Binance's signed USER_DATA API."""
        if not self._api_key or not self._api_secret:
            raise BinanceAuthenticationError("Binance API credentials are not configured")

        timestamp = int(time.time() * 1000)
        query = urlencode({"timestamp": timestamp, "recvWindow": self._recv_window})
        signature = hmac.new(
            self._api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        payload = await self._get_json(
            "/api/v3/account",
            {"timestamp": timestamp, "recvWindow": self._recv_window, "signature": signature},
            symbol="account",
            headers={"X-MBX-APIKEY": self._api_key},
            signed=True,
        )
        return _parse_account(payload)

    # ------------------------------------------------------------------ #
    # HTTP                                                                #
    # ------------------------------------------------------------------ #

    async def _get_json(
        self,
        path: str,
        params: Mapping[str, Any],
        *,
        symbol: str,
        headers: Mapping[str, str] | None = None,
        signed: bool = False,
    ) -> Any:
        url = f"{self._base_url}{path}"
        try:
            if self._http_client is not None:
                response = await self._http_client.get(
                    url, params=params, headers=headers, timeout=self._timeout
                )
            else:
                async with httpx2.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(url, params=params, headers=headers)
        except httpx2.TimeoutException as exc:
            logger.warning("binance market data timeout: %s %s", path, symbol)
            raise NetworkTimeoutError(f"Binance did not answer in time for {symbol}") from exc
        except httpx2.TransportError as exc:
            # Connection refused/reset, DNS failure, TLS failure, ...
            logger.warning("binance market data unreachable: %s %s (%s)", path, symbol, type(exc).__name__)
            raise NetworkTimeoutError(f"Binance could not be reached for {symbol}") from exc

        if response.status_code != 200:
            raise _http_error(response, symbol=symbol, signed=signed)

        try:
            return response.json()
        except ValueError as exc:
            raise MarketDataError(f"Binance returned a non-JSON body for {symbol}") from exc


def _http_error(response: httpx2.Response, *, symbol: str, signed: bool = False) -> MarketDataError:
    """Map a non-200 answer. The body is inspected for Binance's error code only;
    it is never included in the raised message."""
    binance_code: int | None = None
    try:
        body = response.json()
        if isinstance(body, dict) and isinstance(body.get("code"), int):
            binance_code = body["code"]
    except ValueError:
        pass

    if signed and response.status_code == 429:
        return BinanceRateLimitError("Binance rate limit reached")
    if signed and response.status_code in {401, 403}:
        return BinanceAuthenticationError("Binance rejected the configured credentials")
    if signed and binance_code in {-1021}:
        return BinanceTimestampError("Binance rejected the request timestamp")
    if signed and binance_code in {-1022, -2014, -2015}:
        return BinanceAuthenticationError("Binance rejected the configured credentials")

    if response.status_code == 400 and binance_code in _INVALID_SYMBOL_CODES:
        return InvalidSymbolError(f"Binance does not know the symbol {symbol}")
    logger.warning(
        "binance market data HTTP %s for %s (code=%s)", response.status_code, symbol, binance_code
    )
    return BinanceAPIError(
        f"Binance answered HTTP {response.status_code} for {symbol}",
        status_code=response.status_code,
        binance_code=binance_code,
    )


# ---------------------------------------------------------------------- #
# Parsing: raw Binance shapes → domain types                              #
# ---------------------------------------------------------------------- #


def _parse_ticker(payload: Any, *, symbol: str) -> Ticker:
    if not isinstance(payload, dict):
        raise MarketDataError(f"unexpected ticker payload shape for {symbol}")
    try:
        return Ticker(
            symbol=payload["symbol"],
            price=payload["lastPrice"],
            price_change_24h=payload["priceChange"],
            price_change_percent_24h=payload["priceChangePercent"],
            high_24h=payload["highPrice"],
            low_24h=payload["lowPrice"],
            volume_24h=payload["volume"],
        )
    except (KeyError, TypeError, ValidationError) as exc:
        raise MarketDataError(f"unexpected ticker payload for {symbol}") from exc


def _parse_kline(row: Any, *, symbol: str) -> Kline:
    if not isinstance(row, list) or len(row) < 7:
        raise MarketDataError(f"unexpected kline row for {symbol}")
    try:
        return Kline(
            open_time=_from_millis(row[_K_OPEN_TIME]),
            open_price=row[_K_OPEN],
            high_price=row[_K_HIGH],
            low_price=row[_K_LOW],
            close_price=row[_K_CLOSE],
            volume=row[_K_VOLUME],
            close_time=_from_millis(row[_K_CLOSE_TIME]),
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise MarketDataError(f"unexpected kline row for {symbol}") from exc


def _parse_account(payload: Any) -> SpotAccount:
    if not isinstance(payload, dict) or not isinstance(payload.get("balances"), list):
        raise MarketDataError("unexpected account payload shape")
    try:
        balances = tuple(
            AccountBalance(
                asset=balance["asset"],
                free=balance["free"],
                locked=balance["locked"],
            )
            for balance in payload["balances"]
        )
        return SpotAccount(
            account_type=payload["accountType"],
            can_trade=payload["canTrade"],
            balances=balances,
        )
    except (KeyError, TypeError, ValidationError) as exc:
        raise MarketDataError("unexpected account payload") from exc


def _from_millis(value: Any) -> datetime:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("timestamp must be an integer of milliseconds")
    return datetime.fromtimestamp(value / 1000, tz=UTC)
