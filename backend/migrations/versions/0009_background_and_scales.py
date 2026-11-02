"""Datos generales ampliados, antecedentes, foto y escalas de evaluación."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_background_scales"
down_revision: Union[str, None] = "0008_recipient_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_COLUMNS = (
    ("sex", sa.String(length=10)),
    ("birth_country", sa.String(length=60)),
    ("birth_province", sa.String(length=60)),
    ("birth_locality", sa.String(length=100)),
    ("education_level", sa.String(length=40)),
    ("education_title", sa.String(length=120)),
    ("occupation", sa.String(length=40)),
    ("occupation_detail", sa.String(length=200)),
    ("marital_status", sa.String(length=30)),
    ("has_children", sa.Boolean()),
    ("children_details", sa.Text()),
    ("background", sa.JSON()),
)


def upgrade() -> None:
    # "Género" en texto libre se reemplaza por "Sexo" con opciones de la planilla.
    op.drop_column("care_recipients", "gender")
    for name, column_type in NEW_COLUMNS:
        op.add_column("care_recipients", sa.Column(name, column_type, nullable=True))

    op.drop_constraint("ck_recipient_documents_category", "care_recipient_documents", type_="check")
    op.create_check_constraint(
        "ck_recipient_documents_category",
        "care_recipient_documents",
        "category IN ('identity', 'consent', 'study', 'photo', 'other')",
    )

    op.create_table(
        "assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("care_recipient_id", sa.Uuid(), nullable=False),
        sa.Column("scale_code", sa.String(length=20), nullable=False),
        sa.Column("performed_on", sa.Date(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("max_score", sa.Integer(), nullable=False),
        sa.Column("subscores", sa.JSON(), nullable=True),
        sa.Column("interpretation", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("performed_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["care_recipient_id"], ["care_recipients.id"], name="fk_assessments_recipient", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["performed_by_membership_id"], ["organization_memberships.id"], name="fk_assessments_performer", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_assessments"),
    )
    op.create_index("ix_assessments_recipient", "assessments", ["care_recipient_id"])


def downgrade() -> None:
    op.drop_index("ix_assessments_recipient", table_name="assessments")
    op.drop_table("assessments")
    op.drop_constraint("ck_recipient_documents_category", "care_recipient_documents", type_="check")
    op.create_check_constraint(
        "ck_recipient_documents_category",
        "care_recipient_documents",
        "category IN ('identity', 'consent', 'study', 'other')",
    )
    for name, _ in reversed(NEW_COLUMNS):
        op.drop_column("care_recipients", name)
    op.add_column("care_recipients", sa.Column("gender", sa.String(length=40), nullable=True))
