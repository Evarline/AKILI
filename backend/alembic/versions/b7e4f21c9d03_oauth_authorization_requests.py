
"""oauth authorization requests

Revision ID: b7e4f21c9d03
Revises: a3c1d9e7f2b4
Create Date: 2026-09-06 17:10:00.000000

One row per in-flight OAuth authorization-code request (Phase 6.2): the `state`
AKILI issued, who it was issued to, what was sent, the issuer recorded for the
callback check, and the PKCE verifier sealed at rest. Rows are short-lived and
single-use. No token is stored in this table, now or later.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e4f21c9d03"
down_revision: str | Sequence[str] | None = "a3c1d9e7f2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oauth_authorization_requests",
        sa.Column("state", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("client_id", sa.Text(), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("resource", sa.Text(), nullable=False),
        sa.Column("expected_issuer", sa.Text(), nullable=False),
        sa.Column("code_verifier_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("state"),
    )
    op.create_index(
        op.f("ix_oauth_authorization_requests_user_id"),
        "oauth_authorization_requests",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_oauth_authorization_requests_expires_at",
        "oauth_authorization_requests",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_oauth_authorization_requests_expires_at", table_name="oauth_authorization_requests")
    op.drop_index(op.f("ix_oauth_authorization_requests_user_id"), table_name="oauth_authorization_requests")
    op.drop_table("oauth_authorization_requests")
