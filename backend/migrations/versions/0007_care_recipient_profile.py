"""Ficha completa de la persona cuidada y sus contactos."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_recipient_profile"
down_revision: Union[str, None] = "0006_roles_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROFILE_COLUMNS = (
    ("first_name", sa.String(length=80)),
    ("last_name", sa.String(length=80)),
    ("preferred_name", sa.String(length=80)),
    ("birth_date", sa.Date()),
    ("document_type", sa.String(length=20)),
    ("document_number", sa.String(length=30)),
    ("gender", sa.String(length=40)),
    ("nationality", sa.String(length=60)),
    ("languages", sa.String(length=120)),
    ("admission_date", sa.Date()),
    ("room", sa.String(length=40)),
    ("address", sa.String(length=200)),
    ("health_coverage", sa.String(length=120)),
    ("coverage_member_number", sa.String(length=60)),
    ("primary_physician", sa.String(length=120)),
    ("primary_physician_phone", sa.String(length=40)),
    ("allergies", sa.Text()),
    ("relevant_conditions", sa.Text()),
    ("diet_notes", sa.Text()),
    ("mobility_support", sa.Text()),
    ("sensory_communication", sa.Text()),
    ("support_needs", sa.Text()),
    ("life_history", sa.Text()),
    ("preferences", sa.Text()),
    ("routines", sa.Text()),
    ("beliefs", sa.Text()),
)


def upgrade() -> None:
    for name, column_type in PROFILE_COLUMNS:
        op.add_column("care_recipients", sa.Column(name, column_type, nullable=True))

    op.create_table(
        "care_recipient_contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("care_recipient_id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("relationship_label", sa.String(length=60), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("is_emergency", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_legal_representative", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("notes", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["care_recipient_id"],
            ["care_recipients.id"],
            name="fk_recipient_contacts_recipient",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_care_recipient_contacts"),
    )
    op.create_index(
        "ix_care_recipient_contacts_recipient",
        "care_recipient_contacts",
        ["care_recipient_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_care_recipient_contacts_recipient", table_name="care_recipient_contacts")
    op.drop_table("care_recipient_contacts")
    for name, _ in reversed(PROFILE_COLUMNS):
        op.drop_column("care_recipients", name)
