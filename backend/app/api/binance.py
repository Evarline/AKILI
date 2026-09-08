"""Read-only direct Binance Spot account routes.

These routes use the server-side API-key provider. They do not expose Binance
credentials and deliberately contain no order, withdrawal, futures, margin, or
OAuth behavior.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.auth.models import CurrentUser
from app.binance.providers.base import MarketDataProvider
from app.binance.providers.factory import get_market_data_provider
from app.binance.schemas import SpotAccount
from app.core.config import get_settings

router = APIRouter(prefix="/api/v1/binance", tags=["binance"])


class BinanceConnectionResponse(BaseModel):
    """Safe connectivity result; no key material or signed request data."""

    connected: bool
    credentials_configured: bool
    account_type: str | None = None


@router.get("/account", response_model=SpotAccount)
async def account(
    _: CurrentUser = Depends(get_current_user),
    provider: MarketDataProvider = Depends(get_market_data_provider),
) -> SpotAccount:
    """Return the real account and balances for the configured API key."""
    return await provider.get_account()


@router.get("/connection", response_model=BinanceConnectionResponse)
async def connection(
    _: CurrentUser = Depends(get_current_user),
    provider: MarketDataProvider = Depends(get_market_data_provider),
) -> BinanceConnectionResponse:
    """Verify configured credentials with a read-only account request."""
    settings = get_settings()
    if settings.binance_api_key is None or settings.binance_api_secret is None:
        return BinanceConnectionResponse(connected=False, credentials_configured=False)
    account_data = await provider.get_account()
    return BinanceConnectionResponse(
        connected=True,
        credentials_configured=True,
        account_type=account_data.account_type,
    )