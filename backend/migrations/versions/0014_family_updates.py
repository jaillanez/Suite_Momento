"""Novedades para la familia y permiso familiar "Novedades"."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0014_family_updates"
down_revision: Union[str, None] = "0013_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD = "category IN ('medication', 'activities', 'diet')"
_NEW = "category IN ('medication', 'activities', 'diet', 'updates')"
_CHECKS = (("family_authorizations", "ck_family_authorizations_category"), ("family_requests", "ck_family_requests_category"))


def upgrade() -> None:
    for table, name in _CHECKS:
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table, _NEW)
    op.create_table(
        "family_updates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("care_unit_id", sa.Uuid(), sa.ForeignKey("care_units.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("care_recipient_id", sa.Uuid(), sa.ForeignKey("care_recipients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source_entry_id", sa.Uuid(), sa.ForeignKey("care_entries.id", ondelete="RESTRICT")),
        sa.Column("published_by_membership_id", sa.Uuid(), sa.ForeignKey("organization_memberships.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True)),
        sa.Column("withdrawn_by_membership_id", sa.Uuid(), sa.ForeignKey("organization_memberships.id", ondelete="RESTRICT")),
        sa.Column("withdraw_reason", sa.String(length=300)),
    )
    op.create_index("ix_family_updates_care_unit_id", "family_updates", ["care_unit_id"])
    op.create_index("ix_family_updates_care_recipient_id", "family_updates", ["care_recipient_id"])


def downgrade() -> None:
    op.drop_index("ix_family_updates_care_recipient_id", table_name="family_updates")
    op.drop_index("ix_family_updates_care_unit_id", table_name="family_updates")
    op.drop_table("family_updates")
    op.execute("DELETE FROM family_requests WHERE category = 'updates'")
    op.execute("DELETE FROM family_authorizations WHERE category = 'updates'")
    for table, name in _CHECKS:
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table, _OLD)
