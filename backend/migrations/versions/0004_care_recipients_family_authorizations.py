"""Agregar personas cuidadas y autorizaciones familiares."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_family_auth"
down_revision: Union[str, None] = "0003_user_memberships"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "care_recipients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("care_unit_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["care_unit_id"],
            ["care_units.id"],
            name="fk_care_recipients_care_unit",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_care_recipients"),
        sa.UniqueConstraint(
            "care_unit_id",
            "id",
            name="uq_care_recipients_service_id",
        ),
    )
    op.create_index(
        "ix_care_recipients_care_unit_id",
        "care_recipients",
        ["care_unit_id"],
        unique=False,
    )
    op.create_table(
        "family_authorizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("care_recipient_id", sa.Uuid(), nullable=False),
        sa.Column("family_membership_id", sa.Uuid(), nullable=False),
        sa.Column("authorized_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=10), nullable=False),
        sa.Column("can_view", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("can_respond", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("can_request", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "category IN ('medication', 'activities', 'diet')",
            name="ck_family_authorizations_category",
        ),
        sa.ForeignKeyConstraint(
            ["authorized_by_membership_id"],
            ["organization_memberships.id"],
            name="fk_family_auth_authorizer_membership",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["care_recipient_id"],
            ["care_recipients.id"],
            name="fk_family_auth_recipient",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["family_membership_id"],
            ["organization_memberships.id"],
            name="fk_family_auth_family_membership",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_family_authorizations"),
        sa.UniqueConstraint(
            "family_membership_id",
            "care_recipient_id",
            "category",
            name="uq_family_authorizations_person_family_category",
        ),
    )
    op.create_index(
        "ix_family_authorizations_authorized_by_membership_id",
        "family_authorizations",
        ["authorized_by_membership_id"],
        unique=False,
    )
    op.create_index(
        "ix_family_authorizations_care_recipient_id",
        "family_authorizations",
        ["care_recipient_id"],
        unique=False,
    )
    op.create_index(
        "ix_family_authorizations_family_membership_id",
        "family_authorizations",
        ["family_membership_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_family_authorizations_family_membership_id",
        table_name="family_authorizations",
    )
    op.drop_index(
        "ix_family_authorizations_care_recipient_id",
        table_name="family_authorizations",
    )
    op.drop_index(
        "ix_family_authorizations_authorized_by_membership_id",
        table_name="family_authorizations",
    )
    op.drop_table("family_authorizations")
    op.drop_index("ix_care_recipients_care_unit_id", table_name="care_recipients")
    op.drop_table("care_recipients")
