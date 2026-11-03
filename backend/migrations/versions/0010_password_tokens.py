"""Enlaces por correo para invitar y recuperar la contraseña."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_password_tokens"
down_revision: Union[str, None] = "0009_background_scales"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_account_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=10), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("purpose IN ('reset', 'invite')", name="ck_password_tokens_purpose"),
        sa.ForeignKeyConstraint(["user_account_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_password_tokens"),
        sa.UniqueConstraint("token_hash", name="uq_password_tokens_token_hash"),
    )
    op.create_index("ix_password_tokens_user_account_id", "password_tokens", ["user_account_id"])


def downgrade() -> None:
    op.drop_index("ix_password_tokens_user_account_id", table_name="password_tokens")
    op.drop_table("password_tokens")
