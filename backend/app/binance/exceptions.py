"""Market-data errors, provider-neutral.

Every provider failure is translated into one of these, so consumers never
handle HTTP-library or Binance-specific exceptions and never see raw remote
payloads. Messages are safe to log and to store as an error class; they carry
no request parameters beyond the normalised symbol and no response bodies.
Mirrors the shape of `app.llm.base.LLMError`.
"""


class MarketDataError(Exception):
    """Base for every market-data failure."""

    error_class: str = "MARKET_DATA_ERROR"
    retryable: bool = False


class InvalidSymbolError(MarketDataError):
    """The symbol is malformed, or Binance does not know it."""

    error_class = "INVALID_SYMBOL"


class InvalidIntervalError(MarketDataError):
    """The candle interval is not one AKILI's MVP supports."""

    error_class = "INVALID_INTERVAL"


class BinanceAPIError(MarketDataError):
    """Binance answered with an HTTP error status (4xx/5xx) that is not an
    invalid-symbol rejection. Server-side (5xx) failures are retryable."""

    error_class = "BINANCE_API_ERROR"

    def __init__(self, message: str, *, status_code: int, binance_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.binance_code = binance_code
        self.retryable = status_code >= 500


class BinanceAuthenticationError(MarketDataError):
    """Binance rejected the configured API key or signature."""

    error_class = "BINANCE_AUTHENTICATION_FAILED"


class BinanceTimestampError(MarketDataError):
    """The signed request timestamp was outside Binance's accepted window."""

    error_class = "BINANCE_TIMESTAMP_INVALID"


class BinanceRateLimitError(MarketDataError):
    """Binance rate-limited the request."""

    error_class = "BINANCE_RATE_LIMITED"
    retryable = True


class NetworkTimeoutError(MarketDataError):
    """Binance could not be reached in time: timeout or connection failure."""

    error_class = "NETWORK_TIMEOUT"
    retryable = True
