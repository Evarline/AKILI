"""POST /api/v1/chat — send one user message, receive one validated interpretation."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.capabilities import MarketDataFacts
from app.agent.schemas import Interpretation
from app.agent.service import ConversationNotFoundError, handle_chat
from app.auth.dependencies import get_current_user
from app.auth.models import CurrentUser
from app.binance.providers.base import MarketDataProvider
from app.binance.providers.factory import get_market_data_provider
from app.db.session import get_db
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider

router = APIRouter(prefix="/api/v1", tags=["agent"])


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000, description="USER INPUT.")
    conversation_id: UUID | None = Field(
        default=None, description="Continue an existing conversation; omit to start one."
    )

    @field_validator("message")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value.strip()


class ChatResponse(BaseModel):
    """`conversation_id` and `agent_run_id` are APPLICATION-GENERATED. Everything
    inside `response` is MODEL INTERPRETATION, as its provenance field states.

    `market_data` is present only when the turn was a market question AKILI
    fetched data for. It is a BINANCE FACT with the moment it was observed, and
    it is kept beside the interpretation rather than inside it, so a caller can
    always tell which figures came from Binance and which are the model's words.
    """

    conversation_id: UUID
    agent_run_id: UUID
    response: Interpretation
    market_data: MarketDataFacts | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    # Resolved first: an anonymous caller gets 401 before anything else is
    # inspected, and the user is bound from the dependency — never from the body.
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    provider: LLMProvider = Depends(get_llm_provider),
    market_data: MarketDataProvider = Depends(get_market_data_provider),
) -> ChatResponse:
    try:
        outcome = await handle_chat(
            session,
            provider,
            market_data,
            user=current_user,
            message=payload.message,
            conversation_id=payload.conversation_id,
        )
    except ConversationNotFoundError:
        # Same answer whether the id is unknown or belongs to someone else.
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    return ChatResponse(
        conversation_id=outcome.conversation_id,
        agent_run_id=outcome.agent_run_id,
        response=outcome.interpretation,
        market_data=outcome.market_data,
    )
