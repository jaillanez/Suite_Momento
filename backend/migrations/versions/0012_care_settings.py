"""Configuración del registro del cuidado por servicio."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0012_care_settings"
down_revision: Union[str, None] = "0011_care_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("care_units", sa.Column("care_settings", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("care_units", "care_settings")
