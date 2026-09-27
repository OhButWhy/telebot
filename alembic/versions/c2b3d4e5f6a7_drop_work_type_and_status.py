"""drop work_type and status from materials

Materials are now either present or gone, so the soft-delete status column
has no meaning. Rows previously marked deleted are purged for real.

Revision ID: c2b3d4e5f6a7
Revises: d1a2b3c4d5e6
Create Date: 2026-09-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2b3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "d1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM materials WHERE status = 'deleted'")
    op.drop_column("materials", "status")
    op.drop_column("materials", "work_type")


def downgrade() -> None:
    op.add_column(
        "materials",
        sa.Column("work_type", sa.String(), nullable=False,
                  server_default="Материал"),
    )
    op.add_column(
        "materials",
        sa.Column("status", sa.String(), nullable=False,
                  server_default="active"),
    )
    op.execute("UPDATE materials SET status = 'active'")
    op.alter_column("materials", "work_type", server_default=None)
    op.alter_column("materials", "status", server_default=None)
