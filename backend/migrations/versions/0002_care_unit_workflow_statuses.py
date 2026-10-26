"""Agregar estados configurables por servicio."""

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

from momento_api.workflow_defaults import DEFAULT_WORKFLOW_STATUSES


revision: str = "0002_care_workflow_statuses"
down_revision: Union[str, None] = "0001_org_care_units"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "care_unit_workflow_statuses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("care_unit_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("family_visible", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("display_order > 0", name="ck_care_unit_workflow_statuses_order"),
        sa.ForeignKeyConstraint(
            ["care_unit_id"],
            ["care_units.id"],
            name="fk_care_unit_workflow_statuses_care_unit_id_care_units",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_care_unit_workflow_statuses"),
        sa.UniqueConstraint(
            "care_unit_id",
            "code",
            name="uq_care_unit_workflow_statuses_service_code",
        ),
    )

    bind = op.get_bind()
    care_unit_ids = bind.execute(sa.text("SELECT id FROM care_units")).scalars().all()
    rows = []
    for care_unit_id in care_unit_ids:
        for item in DEFAULT_WORKFLOW_STATUSES:
            rows.append(
                {
                    "id": uuid4(),
                    "care_unit_id": care_unit_id,
                    **item,
                }
            )
    if rows:
        op.bulk_insert(
            sa.table(
                "care_unit_workflow_statuses",
                sa.column("id", sa.Uuid()),
                sa.column("care_unit_id", sa.Uuid()),
                sa.column("code", sa.String()),
                sa.column("label", sa.String()),
                sa.column("display_order", sa.Integer()),
                sa.column("is_active", sa.Boolean()),
                sa.column("family_visible", sa.Boolean()),
            ),
            rows,
        )


def downgrade() -> None:
    op.drop_table("care_unit_workflow_statuses")
