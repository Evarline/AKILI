"""Select and build the configured market-data provider."""

from functools import lru_cache

from app.binance.providers.base import MarketDataProvider
from app.binance.providers.rest import BinanceRESTProvider
from app.core.config import get_settings


@lru_cache
def get_market_data_provider() -> MarketDataProvider:
    """The process-wide market-data provider.

    Also the FastAPI dependency for routes that need market data; tests replace
    it through `app.dependency_overrides`. Binance's public REST endpoints are
    the only implementation today — no key, no signature, read-only — and a
    future MCP-backed provider is swapped in here, without any consumer
    changing.
    """
    settings = get_settings()
    return BinanceRESTProvider(
        api_key=settings.binance_api_key,
        api_secret=(
            settings.binance_api_secret.get_secret_value()
            if settings.binance_api_secret is not None
            else None
        ),
        use_testnet=settings.binance_use_testnet,
    )
