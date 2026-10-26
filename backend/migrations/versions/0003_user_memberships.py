"""Agregar identidades y membresías organizacionales."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_user_memberships"
down_revision: Union[str, None] = "0002_care_workflow_statuses"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_care_units_org_id",
        "care_units",
        ["organization_id", "id"],
    )
    op.create_table(
        "user_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_user_accounts"),
    )
    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_account_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("care_unit_id", sa.Uuid(), nullable=True),
        sa.Column("user_group", sa.String(length=11), nullable=False),
        sa.Column("role_label", sa.String(length=80), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "user_group IN ('staff', 'family', 'older_adult')",
            name="ck_membership_user_group",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_organization_memberships_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "care_unit_id"],
            ["care_units.organization_id", "care_units.id"],
            name="fk_membership_care_unit_same_organization",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_account_id"],
            ["user_accounts.id"],
            name="fk_organization_memberships_user_account_id_user_accounts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_memberships"),
        sa.UniqueConstraint(
            "user_account_id",
            "organization_id",
            "care_unit_id",
            "user_group",
            name="uq_membership_user_scope_group",
        ),
    )
    op.create_index(
        "ix_organization_memberships_care_unit_id",
        "organization_memberships",
        ["care_unit_id"],
        unique=False,
    )
    op.create_index(
        "ix_organization_memberships_organization_id",
        "organization_memberships",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_organization_memberships_user_account_id",
        "organization_memberships",
        ["user_account_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organization_memberships_user_account_id",
        table_name="organization_memberships",
    )
    op.drop_index(
        "ix_organization_memberships_organization_id",
        table_name="organization_memberships",
    )
    op.drop_index(
        "ix_organization_memberships_care_unit_id",
        table_name="organization_memberships",
    )
    op.drop_table("organization_memberships")
    op.drop_table("user_accounts")
    op.drop_constraint("uq_care_units_org_id", "care_units", type_="unique")
