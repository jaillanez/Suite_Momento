"""Consentimiento de imagen por persona y foto opcional en las novedades."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0015_family_photos"
down_revision: Union[str, None] = "0014_family_updates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("care_recipients", sa.Column("image_consent_given_by", sa.String(length=160)))
    op.add_column("care_recipients", sa.Column("image_consent_on", sa.Date()))
    op.add_column("care_recipients", sa.Column(
        "image_consent_recorded_by_membership_id", sa.Uuid(),
        sa.ForeignKey("organization_memberships.id", ondelete="RESTRICT", name="fk_care_recipients_image_consent_by"),
    ))
    op.add_column("family_updates", sa.Column("photo_storage_key", sa.String(length=80)))
    op.add_column("family_updates", sa.Column("photo_content_type", sa.String(length=30)))
    op.create_unique_constraint("uq_family_updates_photo_storage_key", "family_updates", ["photo_storage_key"])


def downgrade() -> None:
    op.drop_constraint("uq_family_updates_photo_storage_key", "family_updates", type_="unique")
    op.drop_column("family_updates", "photo_content_type")
    op.drop_column("family_updates", "photo_storage_key")
    op.drop_constraint("fk_care_recipients_image_consent_by", "care_recipients", type_="foreignkey")
    op.drop_column("care_recipients", "image_consent_recorded_by_membership_id")
    op.drop_column("care_recipients", "image_consent_on")
    op.drop_column("care_recipients", "image_consent_given_by")
