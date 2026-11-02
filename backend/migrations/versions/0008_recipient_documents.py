"""Documentos adjuntos a la ficha de la persona cuidada."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_recipient_documents"
down_revision: Union[str, None] = "0007_recipient_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "care_recipient_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("care_recipient_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("original_filename", sa.String(length=200), nullable=False),
        sa.Column("content_type", sa.String(length=60), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=80), nullable=False),
        sa.Column("uploaded_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "category IN ('identity', 'consent', 'study', 'other')",
            name="ck_recipient_documents_category",
        ),
        sa.ForeignKeyConstraint(["care_recipient_id"], ["care_recipients.id"], name="fk_recipient_documents_recipient", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["uploaded_by_membership_id"], ["organization_memberships.id"], name="fk_recipient_documents_uploader", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_care_recipient_documents"),
        sa.UniqueConstraint("storage_key", name="uq_recipient_documents_storage_key"),
    )
    op.create_index("ix_recipient_documents_recipient", "care_recipient_documents", ["care_recipient_id"])


def downgrade() -> None:
    op.drop_index("ix_recipient_documents_recipient", table_name="care_recipient_documents")
    op.drop_table("care_recipient_documents")
