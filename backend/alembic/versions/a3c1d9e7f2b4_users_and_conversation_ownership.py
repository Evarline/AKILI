"""users and conversation ownership

Revision ID: a3c1d9e7f2b4
Revises: 91f62ba7bf45
Create Date: 2026-09-06 14:20:00.000000

Adds the `users` table and gives every conversation a non-null owner.

Existing conversations
----------------------
A conversation created before this revision has no owner. The migration never
deletes or orphans it. If any such rows exist, it assigns them to the development
fixed user named by DEV_FIXED_USER_ID (creating that DEVELOPMENT-origin user if
needed) — and only when APP_ENV=development. In any other environment, or when
no DEV_FIXED_USER_ID is configured, the migration stops with a clear message
and, thanks to transactional DDL, leaves the schema exactly as it was.

Downgrade removes the ownership column and the users table. Ownership
information is lost on downgrade; the conversations themselves are kept.
"""

from typing import Sequence, Union
from uuid import UUID

import sqlalchemy as sa
from alembic import op

from app.core.config import get_settings

# revision identifiers, used by Alembic.
revision: str = "a3c1d9e7f2b4"
down_revision: Union[str, Sequence[str], None] = "91f62ba7bf45"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FK_NAME = "fk_conversations_user_id_users"
INDEX_NAME = "ix_conversations_user_id_updated_at"


def _backfill_unowned_conversations() -> None:
    """Give pre-existing conversations an owner, or refuse loudly."""
    bind = op.get_bind()
    unowned = bind.execute(
        sa.text("SELECT count(*) FROM conversations WHERE user_id IS NULL")
    ).scalar_one()
    if unowned == 0:
        return

    settings = get_settings()
    if settings.app_env != "development":
        raise RuntimeError(
            f"{unowned} conversation(s) have no owner and APP_ENV={settings.app_env!r}. "
            "Backfilling to a development user is only allowed in development. "
            "Nothing was changed."
        )
    owner: UUID | None = settings.dev_fixed_user_id
    if owner is None:
        raise RuntimeError(
            f"{unowned} conversation(s) have no owner. Set DEV_FIXED_USER_ID in the root "
            ".env to the development user that should own them, then re-run "
            "`alembic upgrade head`. Nothing was changed."
        )

    bind.execute(
        sa.text(
            "INSERT INTO users (id, status, origin) VALUES (:id, 'ACTIVE', 'DEVELOPMENT') "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"id": owner},
    )
    bind.execute(
        sa.text("UPDATE conversations SET user_id = :id WHERE user_id IS NULL"),
        {"id": owner},
    )


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name="ck_users_status"),
        sa.CheckConstraint("origin IN ('DEVELOPMENT', 'PROVISIONED')", name="ck_users_origin"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Nullable first so existing rows can be assigned an owner, then tightened.
    op.add_column("conversations", sa.Column("user_id", sa.Uuid(), nullable=True))
    _backfill_unowned_conversations()
    op.alter_column("conversations", "user_id", nullable=False)
    op.create_foreign_key(
        FK_NAME, "conversations", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index(INDEX_NAME, "conversations", ["user_id", "updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="conversations")
    op.drop_constraint(FK_NAME, "conversations", type_="foreignkey")
    op.drop_column("conversations", "user_id")
    op.drop_table("users")
