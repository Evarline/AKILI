"""Market-data providers. Consumers import the contract from `.base`; only
composition code (a factory, a test) names a concrete implementation."""

from app.binance.providers.base import MarketDataProvider

__all__ = ["MarketDataProvider"]
