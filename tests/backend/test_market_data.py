"""BinanceRESTProvider against a fake Binance. No network, no database.

The fake answers with Binance's documented response shapes (a dict for
/api/v3/ticker/24hr, positional arrays for /api/v3/klines) so the parsing
under test is the real one. Every HTTP outcome is produced by an
`httpx2.MockTransport` handler.
"""

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx2
import pytest

from app.binance.exceptions import (
    BinanceAPIError,
    InvalidIntervalError,
    InvalidSymbolError,
    MarketDataError,
    NetworkTimeoutError,
)
from app.binance.providers.base import MarketDataProvider
from app.binance.providers.rest import BinanceRESTProvider
from app.binance.schemas import SUPPORTED_INTERVALS, Kline, Ticker, normalize_symbol

# Shapes copied from Binance's public Spot API documentation.
TICKER_24HR = {
    "symbol": "BTCUSDT",
    "priceChange": "-1234.56000000",
    "priceChangePercent": "-1.532",
    "weightedAvgPrice": "79999.12345678",
    "prevClosePrice": "80554.56000000",
    "lastPrice": "79320.00000000",
    "lastQty": "0.00100000",
    "bidPrice": "79319.99000000",
    "bidQty": "1.00000000",
    "askPrice": "79320.00000000",
    "askQty": "2.00000000",
    "openPrice": "80554.56000000",
    "highPrice": "81000.00000000",
    "lowPrice": "78500.00000000",
    "volume": "12345.67890000",
    "quoteVolume": "987654321.00000000",
    "openTime": 1788600000000,
    "closeTime": 1788686399999,
    "firstId": 1,
    "lastId": 2,
    "count": 2,
}
KLINES = [
    [1788600000000, "80000.00", "80500.00", "79800.00", "80250.00", "12.5", 1788603599999,
     "1000000.00", 150, "6.0", "480000.00", "0"],
    [1788603600000, "80250.00", "80300.00", "79900.00", "79950.00", "9.75", 1788607199999,
     "780000.00", 120, "4.5", "360000.00", "0"],
]

Handler = Callable[[httpx2.Request], httpx2.Response]


def provider_with(handler: Handler) -> tuple[BinanceRESTProvider, list[httpx2.Request]]:
    """A provider whose HTTP goes to `handler`; also returns the captured requests."""
    seen: list[httpx2.Request] = []

    def recording(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return handler(request)

    client = httpx2.AsyncClient(transport=httpx2.MockTransport(recording))
    return BinanceRESTProvider(http_client=client), seen


def binance_ok(request: httpx2.Request) -> httpx2.Response:
    path = request.url.path
    if path == "/api/v3/ticker/24hr":
        return httpx2.Response(200, json=TICKER_24HR)
    if path == "/api/v3/klines":
        return httpx2.Response(200, json=KLINES)
    return httpx2.Response(404, json={"code": -1102, "msg": "Unknown"})


def binance_error(status: int, body: Any) -> Handler:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status, json=body) if body is not None else httpx2.Response(status, text="<html>")

    return handler


def run(coro):  # noqa: ANN001, ANN201 - tiny test helper
    return asyncio.run(coro)


# --------------------------------------------------------------------------- #
# Contract                                                                     #
# --------------------------------------------------------------------------- #


def test_binance_rest_provider_satisfies_the_contract() -> None:
    provider, _ = provider_with(binance_ok)
    assert isinstance(provider, MarketDataProvider)
    assert provider.name == "binance-rest"


def test_supported_intervals_are_the_mvp_set() -> None:
    assert SUPPORTED_INTERVALS == ("1h", "4h", "1d")


# --------------------------------------------------------------------------- #
# 1. Ticker parsing                                                            #
# --------------------------------------------------------------------------- #


def test_get_ticker_parses_the_24hr_ticker() -> None:
    provider, seen = provider_with(binance_ok)

    ticker = run(provider.get_ticker("BTCUSDT"))

    assert isinstance(ticker, Ticker)
    assert ticker == Ticker(
        symbol="BTCUSDT",
        price=Decimal("79320.00000000"),
        price_change_24h=Decimal("-1234.56000000"),
        price_change_percent_24h=Decimal("-1.532"),
        high_24h=Decimal("81000.00000000"),
        low_24h=Decimal("78500.00000000"),
        volume_24h=Decimal("12345.67890000"),
    )
    # Exactness preserved: no float went through.
    assert type(ticker.price) is Decimal and str(ticker.price) == "79320.00000000"
    # The request is the documented public endpoint, unauthenticated.
    request = seen[0]
    assert request.method == "GET"
    assert str(request.url) == "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
    assert "authorization" not in {k.lower() for k in request.headers}
    assert "x-mbx-apikey" not in {k.lower() for k in request.headers}


def test_ticker_hides_raw_binance_fields() -> None:
    provider, _ = provider_with(binance_ok)
    ticker = run(provider.get_ticker("BTCUSDT"))
    dumped = ticker.model_dump()
    for raw_name in ("lastPrice", "priceChange", "weightedAvgPrice", "bidPrice", "quoteVolume", "count"):
        assert raw_name not in dumped
    # Decimals serialise as strings, as everywhere else in AKILI (contract §3).
    assert json.loads(ticker.model_dump_json())["price"] == "79320.00000000"


# --------------------------------------------------------------------------- #
# 2. Kline parsing                                                             #
# --------------------------------------------------------------------------- #


def test_get_klines_converts_positional_arrays_into_klines() -> None:
    provider, seen = provider_with(binance_ok)

    klines = run(provider.get_klines("BTCUSDT", interval="1h", limit=2))

    assert len(klines) == 2 and all(isinstance(k, Kline) for k in klines)
    first = klines[0]
    assert first.open_time == datetime.fromtimestamp(1788600000000 / 1000, tz=UTC)
    assert first.open_time == datetime(2026, 9, 5, 9, 20, tzinfo=UTC)  # ms epoch → aware UTC
    assert first.open_time.tzinfo is not None
    assert first.open_price == Decimal("80000.00")
    assert first.high_price == Decimal("80500.00")
    assert first.low_price == Decimal("79800.00")
    assert first.close_price == Decimal("80250.00")
    assert first.volume == Decimal("12.5")
    assert first.close_time == datetime.fromtimestamp(1788603599999 / 1000, tz=UTC)
    assert klines[1].close_price == Decimal("79950.00")
    # Only the seven fields AKILI defines; the other five array positions are dropped.
    assert set(first.model_dump()) == {
        "open_time", "open_price", "high_price", "low_price", "close_price", "volume", "close_time",
    }
    url = seen[0].url
    assert url.path == "/api/v3/klines"
    assert dict(url.params) == {"symbol": "BTCUSDT", "interval": "1h", "limit": "2"}


def test_get_klines_defaults_to_one_hour_and_one_hundred() -> None:
    provider, seen = provider_with(binance_ok)
    run(provider.get_klines("ETHUSDT"))
    assert dict(seen[0].url.params) == {"symbol": "ETHUSDT", "interval": "1h", "limit": "100"}


# --------------------------------------------------------------------------- #
# 3. Intervals                                                                 #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("bad", ["1m", "15m", "1w", "1H", "hour", ""])
def test_unsupported_interval_is_rejected_before_any_request(bad: str) -> None:
    provider, seen = provider_with(binance_ok)
    with pytest.raises(InvalidIntervalError) as excinfo:
        run(provider.get_klines("BTCUSDT", interval=bad))  # type: ignore[arg-type]
    assert "1h, 4h, 1d" in str(excinfo.value)
    assert seen == []


@pytest.mark.parametrize("bad_limit", [0, -1, 1001, 2.5, True])
def test_out_of_range_limit_is_rejected_before_any_request(bad_limit: Any) -> None:
    provider, seen = provider_with(binance_ok)
    with pytest.raises(ValueError, match="between 1 and 1000"):
        run(provider.get_klines("BTCUSDT", limit=bad_limit))
    assert seen == []


# --------------------------------------------------------------------------- #
# 4. HTTP errors                                                               #
# --------------------------------------------------------------------------- #


def test_unknown_symbol_400_is_invalid_symbol_error() -> None:
    provider, _ = provider_with(binance_error(400, {"code": -1121, "msg": "Invalid symbol."}))
    with pytest.raises(InvalidSymbolError) as excinfo:
        run(provider.get_ticker("NOPEUSDT"))
    assert "NOPEUSDT" in str(excinfo.value)
    assert "Invalid symbol." not in str(excinfo.value)  # remote text never surfaces
    assert excinfo.value.retryable is False


def test_other_400_is_binance_api_error_with_code() -> None:
    provider, _ = provider_with(binance_error(400, {"code": -1130, "msg": "Data sent for parameter 'x' is not valid."}))
    with pytest.raises(BinanceAPIError) as excinfo:
        run(provider.get_klines("BTCUSDT"))
    assert excinfo.value.status_code == 400
    assert excinfo.value.binance_code == -1130
    assert excinfo.value.retryable is False
    assert "not valid" not in str(excinfo.value)


def test_404_is_binance_api_error() -> None:
    provider, _ = provider_with(binance_error(404, None))
    with pytest.raises(BinanceAPIError) as excinfo:
        run(provider.get_ticker("BTCUSDT"))
    assert excinfo.value.status_code == 404 and excinfo.value.binance_code is None


@pytest.mark.parametrize("status", [429, 500, 502, 503])
def test_server_side_and_rate_limit_errors(status: int) -> None:
    provider, _ = provider_with(binance_error(status, {"code": -1003, "msg": "Too many requests."}))
    with pytest.raises(BinanceAPIError) as excinfo:
        run(provider.get_ticker("BTCUSDT"))
    assert excinfo.value.status_code == status
    assert excinfo.value.retryable is (status >= 500)


def test_malformed_success_bodies_are_market_data_errors() -> None:
    def not_json(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, text="<html>maintenance</html>")

    provider, _ = provider_with(not_json)
    with pytest.raises(MarketDataError, match="non-JSON"):
        run(provider.get_ticker("BTCUSDT"))

    provider, _ = provider_with(lambda r: httpx2.Response(200, json={"symbol": "BTCUSDT"}))
    with pytest.raises(MarketDataError, match="unexpected ticker payload"):
        run(provider.get_ticker("BTCUSDT"))

    provider, _ = provider_with(lambda r: httpx2.Response(200, json=[[1788600000000, "1", "2"]]))
    with pytest.raises(MarketDataError, match="unexpected kline row"):
        run(provider.get_klines("BTCUSDT"))


# --------------------------------------------------------------------------- #
# 5. Timeouts and connection failures                                          #
# --------------------------------------------------------------------------- #


def test_timeout_is_network_timeout_error() -> None:
    def slow(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("read timed out", request=request)

    provider, _ = provider_with(slow)
    with pytest.raises(NetworkTimeoutError) as excinfo:
        run(provider.get_ticker("BTCUSDT"))
    assert excinfo.value.retryable is True
    assert isinstance(excinfo.value.__cause__, httpx2.TimeoutException)


def test_connection_failure_is_network_timeout_error() -> None:
    def refused(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("connection refused", request=request)

    provider, _ = provider_with(refused)
    with pytest.raises(NetworkTimeoutError):
        run(provider.get_klines("BTCUSDT", interval="4h"))


def test_default_client_uses_the_configured_timeout() -> None:
    provider = BinanceRESTProvider(timeout_seconds=10.0)
    assert provider._timeout == httpx2.Timeout(10.0)  # noqa: SLF001 - configuration check


# --------------------------------------------------------------------------- #
# Symbols                                                                      #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("btcusdt", "BTCUSDT"),
        ("btc/usdt", "BTCUSDT"),
        (" BTC-USDT ", "BTCUSDT"),
        ("eth_btc", "ETHBTC"),
        ("BTC:USDT", "BTCUSDT"),
        ("1inch/usdt", "1INCHUSDT"),
    ],
)
def test_symbol_normalisation(raw: str, expected: str) -> None:
    assert normalize_symbol(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "BTC", "BTC$USDT", "x" * 21, "btc usdt!"])
def test_malformed_symbols_are_rejected_before_any_request(raw: str) -> None:
    provider, seen = provider_with(binance_ok)
    with pytest.raises(InvalidSymbolError):
        run(provider.get_ticker(raw))
    assert seen == []


def test_provider_sends_the_normalised_symbol() -> None:
    provider, seen = provider_with(binance_ok)
    run(provider.get_ticker("btc/usdt"))
    assert dict(seen[0].url.params) == {"symbol": "BTCUSDT"}
