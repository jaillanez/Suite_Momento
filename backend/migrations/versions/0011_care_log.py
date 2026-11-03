"""Registro diario del cuidado y pendientes para la entrega de turno."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_care_log"
down_revision: Union[str, None] = "0010_password_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _fk(column: str, table: str) -> sa.Column:
    return sa.Column(column, sa.Uuid(), sa.ForeignKey(f"{table}.id", ondelete="RESTRICT"))


def upgrade() -> None:
    op.create_table(
        "care_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("care_unit_id", sa.Uuid(), sa.ForeignKey("care_units.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("care_recipient_id", sa.Uuid(), sa.ForeignKey("care_recipients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("important", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by_membership_id", sa.Uuid(), sa.ForeignKey("organization_memberships.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("voided_at", sa.DateTime(timezone=True)),
        _fk("voided_by_membership_id", "organization_memberships"),
        sa.Column("void_reason", sa.String(length=300)),
        sa.CheckConstraint(
            "category IN ('food', 'hygiene', 'sleep', 'mood', 'activity', 'health', 'incident', 'other')",
            name="ck_care_entries_category",
        ),
    )
    op.create_index("ix_care_entries_care_unit_id", "care_entries", ["care_unit_id"])
    op.create_index("ix_care_entries_care_recipient_id", "care_entries", ["care_recipient_id"])
    op.create_index("ix_care_entries_occurred_at", "care_entries", ["occurred_at"])

    op.create_table(
        "care_tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("care_unit_id", sa.Uuid(), sa.ForeignKey("care_units.id", ondelete="RESTRICT"), nullable=False),
        _fk("care_recipient_id", "care_recipients"),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("details", sa.Text()),
        sa.Column("due_on", sa.Date()),
        sa.Column("status", sa.String(length=10), server_default="open", nullable=False),
        sa.Column("created_by_membership_id", sa.Uuid(), sa.ForeignKey("organization_memberships.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        _fk("closed_by_membership_id", "organization_memberships"),
        sa.Column("closing_note", sa.String(length=500)),
        sa.CheckConstraint("status IN ('open', 'done', 'cancelled')", name="ck_care_tasks_status"),
    )
    op.create_index("ix_care_tasks_care_unit_id", "care_tasks", ["care_unit_id"])
    op.create_index("ix_care_tasks_care_recipient_id", "care_tasks", ["care_recipient_id"])


def downgrade() -> None:
    op.drop_index("ix_care_tasks_care_recipient_id", table_name="care_tasks")
    op.drop_index("ix_care_tasks_care_unit_id", table_name="care_tasks")
    op.drop_table("care_tasks")
    op.drop_index("ix_care_entries_occurred_at", table_name="care_entries")
    op.drop_index("ix_care_entries_care_recipient_id", table_name="care_entries")
    op.drop_index("ix_care_entries_care_unit_id", table_name="care_entries")
    op.drop_table("care_entries")
