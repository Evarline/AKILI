"""ORM models: users, conversations, messages, and agent runs.

This is not the final AKILI schema. Proposals, approvals, and executions arrive
in later phases (docs/01-AGENT-CONTRACT.md §6–§7). What exists here is the
minimum needed to hold a conversation, to record each model interaction, and to
give every conversation an owner.

Data minimisation: no raw prompts, no raw provider responses, and no secrets are
stored. An agent run keeps the *validated* interpretation, token counts, and an
error class — enough to audit and debug, nothing more. A user is an opaque
identity: it carries no credential and no login method (those belong to a future
`user_identities` table, so adding a login method never reshapes `users`).
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

USER_STATUS_ACTIVE = "ACTIVE"
USER_STATUS_DISABLED = "DISABLED"
USER_STATUSES = (USER_STATUS_ACTIVE, USER_STATUS_DISABLED)

# Where the row came from. DEVELOPMENT rows are seeded by `app.auth.seed` for the
# fixed-user mode and are refused outside APP_ENV=development, whatever the
# configuration says (app/auth/dependencies.py). PROVISIONED is reserved for
# real sign-up, which does not exist yet.
USER_ORIGIN_DEVELOPMENT = "DEVELOPMENT"
USER_ORIGIN_PROVISIONED = "PROVISIONED"
USER_ORIGINS = (USER_ORIGIN_DEVELOPMENT, USER_ORIGIN_PROVISIONED)


def _in_list(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class User(Base):
    """An AKILI user: a stable, opaque id that owns conversations (and, in a later
    phase, a Binance connection). Nothing here authenticates anyone."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(_in_list("status", USER_STATUSES), name="ck_users_status"),
        CheckConstraint(_in_list("origin", USER_ORIGINS), name="ck_users_origin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=USER_STATUS_ACTIVE)
    origin: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Conversation(Base):
    """Owned by exactly one user. Every read and continuation is filtered by that
    owner in the service layer, so another user sees "not found", never content."""

    __tablename__ = "conversations"
    __table_args__ = (
        # "This user's recent conversations": the listing a UI will ask for.
        Index("ix_conversations_user_id_updated_at", "user_id", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        order_by="Message.created_at",
        cascade="all, delete-orphan",
    )


class OAuthAuthorizationRequest(Base):
    """One in-flight OAuth authorization-code request, from redirect to callback.

    Owned by the user who started it. The row exists so that, when the browser
    comes back with `code` and `state`, AKILI can prove the state is one it
    issued, to this user, recently, and can recover the PKCE verifier and the
    issuer it recorded before redirecting (MCP authorization spec). The verifier
    is stored sealed: a database read alone must not yield a usable secret.
    Rows are single-use and short-lived; no token is ever stored here.
    """

    __tablename__ = "oauth_authorization_requests"
    __table_args__ = (
        # Sweeping expired requests is a range scan on this column.
        Index("ix_oauth_authorization_requests_expires_at", "expires_at"),
    )

    # The `state` value itself: random, unguessable, and unique by construction.
    state: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Which authorization server this request targets ("binance" today).
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    # Exactly what was sent, so the token exchange repeats it verbatim.
    client_id: Mapped[str] = mapped_column(Text, nullable=False)
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)
    resource: Mapped[str] = mapped_column(Text, nullable=False)
    # Recorded before the redirect; the callback's `iss` must match it (RFC 9207).
    expected_issuer: Mapped[str] = mapped_column(Text, nullable=False)
    code_verifier_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Message(Base):
    """One turn. `role` is 'user' (USER INPUT) or 'assistant' (MODEL INTERPRETATION)."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class AgentRun(Base):
    """One model interaction: which message triggered it, what came back, or why not."""

    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    assistant_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(16), nullable=False)  # RUNNING|COMPLETED|FAILED
    intent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    error_class: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # The validated interpretation only — never the raw provider payload.
    interpretation: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
