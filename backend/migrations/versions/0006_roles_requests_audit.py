"""Agregar puestos del personal, bandeja persistente y auditoría."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_roles_requests"
down_revision: Union[str, None] = "0005_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organization_memberships",
        sa.Column("staff_role", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "organization_memberships",
        sa.Column(
            "handles_inbox",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    # Los vínculos existentes solo tenían una función descriptiva de texto libre.
    # No se derivan permisos de texto libre: solo se reconocen, por igualdad
    # exacta, las etiquetas que generaba el propio sistema. El resto queda como
    # cuidador (menor acceso) y el encargado debe asignar el puesto a mano.
    op.execute(
        """
        UPDATE organization_memberships
        SET staff_role = CASE
            WHEN role_label IN ('Encargado de residencia', 'Encargada de residencia', 'Encargado/a')
                THEN 'manager'
            WHEN role_label = 'Médico/a' THEN 'physician'
            ELSE 'caregiver'
        END
        WHERE user_group = 'staff'
        """
    )
    op.create_check_constraint(
        "ck_membership_staff_role",
        "organization_memberships",
        "(user_group = 'staff' AND staff_role IS NOT NULL) "
        "OR (user_group <> 'staff' AND staff_role IS NULL)",
    )
    op.create_check_constraint(
        "ck_membership_staff_role_value",
        "organization_memberships",
        "staff_role IS NULL OR staff_role IN "
        "('manager', 'administrative', 'physician', 'caregiver')",
    )
    op.create_check_constraint(
        "ck_membership_inbox_staff",
        "organization_memberships",
        "handles_inbox = false OR user_group = 'staff'",
    )

    op.add_column(
        "family_authorizations",
        sa.Column("revoked_by_membership_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_family_auth_revoked_by",
        "family_authorizations",
        "organization_memberships",
        ["revoked_by_membership_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "family_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("care_unit_id", sa.Uuid(), nullable=False),
        sa.Column("care_recipient_id", sa.Uuid(), nullable=False),
        sa.Column("family_membership_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=10), nullable=False),
        sa.Column("subject", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status_code", sa.String(length=40), nullable=False),
        sa.Column("assigned_to_membership_id", sa.Uuid(), nullable=True),
        sa.Column("shared_response", sa.Text(), nullable=True),
        sa.Column("responded_by_membership_id", sa.Uuid(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "category IN ('medication', 'activities', 'diet')",
            name="ck_family_requests_category",
        ),
        sa.ForeignKeyConstraint(["care_unit_id"], ["care_units.id"], name="fk_family_requests_unit", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["care_recipient_id"], ["care_recipients.id"], name="fk_family_requests_recipient", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["family_membership_id"], ["organization_memberships.id"], name="fk_family_requests_family", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_to_membership_id"], ["organization_memberships.id"], name="fk_family_requests_assignee", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["responded_by_membership_id"], ["organization_memberships.id"], name="fk_family_requests_responder", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_family_requests"),
    )
    op.create_index("ix_family_requests_care_unit_id", "family_requests", ["care_unit_id"])
    op.create_index("ix_family_requests_care_recipient_id", "family_requests", ["care_recipient_id"])
    op.create_index("ix_family_requests_family_membership_id", "family_requests", ["family_membership_id"])
    op.create_index("ix_family_requests_assigned_to", "family_requests", ["assigned_to_membership_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actor_account_id", sa.Uuid(), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=True),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["actor_account_id"], ["user_accounts.id"], name="fk_audit_events_actor", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_audit_events_organization", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
    )
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])
    op.create_index("ix_audit_events_actor_account_id", "audit_events", ["actor_account_id"])
    op.create_index("ix_audit_events_organization_id", "audit_events", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_organization_id", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_account_id", table_name="audit_events")
    op.drop_index("ix_audit_events_occurred_at", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_family_requests_assigned_to", table_name="family_requests")
    op.drop_index("ix_family_requests_family_membership_id", table_name="family_requests")
    op.drop_index("ix_family_requests_care_recipient_id", table_name="family_requests")
    op.drop_index("ix_family_requests_care_unit_id", table_name="family_requests")
    op.drop_table("family_requests")
    op.drop_constraint("fk_family_auth_revoked_by", "family_authorizations", type_="foreignkey")
    op.drop_column("family_authorizations", "revoked_by_membership_id")
    op.drop_constraint("ck_membership_inbox_staff", "organization_memberships", type_="check")
    op.drop_constraint("ck_membership_staff_role_value", "organization_memberships", type_="check")
    op.drop_constraint("ck_membership_staff_role", "organization_memberships", type_="check")
    op.drop_column("organization_memberships", "handles_inbox")
    op.drop_column("organization_memberships", "staff_role")
