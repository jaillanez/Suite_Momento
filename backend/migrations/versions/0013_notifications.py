"""Avisos dentro de Momento (web y futura app móvil)."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0013_notifications"
down_revision: Union[str, None] = "0012_care_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_account_id", sa.Uuid(), sa.ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("care_unit_id", sa.Uuid(), sa.ForeignKey("care_units.id", ondelete="CASCADE")),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.String(length=500)),
        sa.Column("target_type", sa.String(length=40)),
        sa.Column("target_id", sa.Uuid()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_notifications_user_account_id", "notifications", ["user_account_id"])


def downgrade() -> None:
    op.drop_index("ix_notifications_user_account_id", table_name="notifications")
    op.drop_table("notifications")
