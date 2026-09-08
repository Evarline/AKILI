"""Signed, read-only Binance Spot account access without real credentials."""

import asyncio
import hashlib
import hmac
from collections.abc import Callable
from decimal import Decimal
from urllib.parse import urlencode

import httpx2
import pytest
from app.binance.exceptions import (
    BinanceAuthenticationError,
    BinanceRateLimitError,
    BinanceTimestampError,
)
from app.binance.providers.rest import BinanceRESTProvider
from app.core.config import Settings
from pydantic import SecretStr

Handler = Callable[[httpx2.Request], httpx2.Response]

ACCOUNT = {
    "makerCommission": 15,
    "takerCommission": 25,
    "accountType": "SPOT",
    "canTrade": True,
    "canWithdraw": False,
    "canDeposit": True,
    "updateTime": 1788600000000,
    "balances": [
        {"asset": "BTC", "free": "0.10000000", "locked": "0.01000000"},
        {"asset": "USDT", "free": "250.50", "locked": "0"},
    ],
    "permissions": ["SPOT"],
}


def run(coro):
    return asyncio.run(coro)


def provider_with(handler: Handler, **kwargs: object) -> tuple[BinanceRESTProvider, list[httpx2.Request]]:
    seen: list[httpx2.Request] = []

    def recording(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return handler(request)

    client = httpx2.AsyncClient(transport=httpx2.MockTransport(recording))
    return BinanceRESTProvider(http_client=client, **kwargs), seen


def test_settings_load_direct_binance_credentials_without_exposing_secret() -> None:
    settings = Settings(
        _env_file=None,
        binance_api_key="test-key",
        binance_api_secret=SecretStr("test-secret"),
        binance_use_testnet=True,
    )

    assert settings.binance_api_key == "test-key"
    assert settings.binance_api_secret is not None
    assert settings.binance_api_secret.get_secret_value() == "test-secret"
    assert "test-secret" not in repr(settings)
    assert settings.binance_use_testnet is True


def test_missing_credentials_fail_before_network() -> None:
    provider, seen = provider_with(lambda request: httpx2.Response(500))

    with pytest.raises(BinanceAuthenticationError, match="not configured"):
        run(provider.get_account())

    assert seen == []


def test_account_request_uses_api_key_and_hmac_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    fixed_time = 1788600000.123
    monkeypatch.setattr("app.binance.providers.rest.time.time", lambda: fixed_time)
    provider, seen = provider_with(
        lambda request: httpx2.Response(200, json=ACCOUNT),
        api_key="test-api-key",
        api_secret="test-api-secret",
    )

    account = run(provider.get_account())

    assert account.account_type == "SPOT"
    assert account.can_trade is True
    assert [balance.model_dump() for balance in account.balances] == [
        {"asset": "BTC", "free": Decimal("0.10000000"), "locked": Decimal("0.01000000")},
        {"asset": "USDT", "free": Decimal("250.50"), "locked": Decimal(0)},
    ]
    request = seen[0]
    assert request.url.path == "/api/v3/account"
    assert request.headers["X-MBX-APIKEY"] == "test-api-key"
    assert "test-api-secret" not in str(request.url)
    query = dict(request.url.params)
    unsigned = urlencode({"timestamp": query["timestamp"], "recvWindow": query["recvWindow"]})
    expected = hmac.new(b"test-api-secret", unsigned.encode(), hashlib.sha256).hexdigest()
    assert query["signature"] == expected


def test_testnet_switch_uses_binance_spot_testnet(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.binance.providers.rest.time.time", lambda: 1788600000)
    provider, seen = provider_with(
        lambda request: httpx2.Response(200, json=ACCOUNT),
        api_key="test-api-key",
        api_secret="test-api-secret",
        use_testnet=True,
    )

    run(provider.get_account())

    assert seen[0].url.host == "testnet.binance.vision"


@pytest.mark.parametrize(
    ("status", "body", "error"),
    [
        (401, {"code": -2015, "msg": "Invalid API-key"}, BinanceAuthenticationError),
        (400, {"code": -1022, "msg": "Invalid signature"}, BinanceAuthenticationError),
        (400, {"code": -1021, "msg": "Timestamp outside recvWindow"}, BinanceTimestampError),
        (429, {"code": -1003, "msg": "Too many requests"}, BinanceRateLimitError),
    ],
)
def test_authenticated_binance_errors_are_safe(
    status: int, body: dict[str, object], error: type[Exception]
) -> None:
    provider, _ = provider_with(
        lambda request: httpx2.Response(status, json=body),
        api_key="test-api-key",
        api_secret="test-api-secret",
    )

    with pytest.raises(error) as excinfo:
        run(provider.get_account())

    assert "test-api-secret" not in str(excinfo.value)
    assert "Invalid API-key" not in str(excinfo.value)
    assert "Invalid signature" not in str(excinfo.value)


def test_account_parser_drops_unneeded_binance_fields() -> None:
    provider, _ = provider_with(
        lambda request: httpx2.Response(200, json=ACCOUNT),
        api_key="test-api-key",
        api_secret="test-api-secret",
    )

    dumped = run(provider.get_account()).model_dump()

    assert set(dumped) == {"account_type", "can_trade", "balances"}
    assert dumped["balances"][0]["asset"] == "BTC"
    assert "permissions" not in dumped
    assert "canWithdraw" not in dumped
