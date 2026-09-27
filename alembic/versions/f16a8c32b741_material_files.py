"""support multiple files per material

Revision ID: f16a8c32b741
Revises: e04b7c91d632
Create Date: 2026-09-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f16a8c32b741"
down_revision: Union[str, Sequence[str], None] = "e04b7c91d632"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "material_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("telegram_file_id", sa.String(), nullable=False),
        sa.Column("file_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["material_id"], ["materials.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_material_files_id"), "material_files", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_material_files_material_id"),
        "material_files",
        ["material_id"],
        unique=False,
    )
    op.execute(
        sa.text(
            "INSERT INTO material_files "
            "(material_id, telegram_file_id) "
            "SELECT id, telegram_file_id FROM materials"
        )
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_material_files_material_id"),
        table_name="material_files",
    )
    op.drop_index(op.f("ix_material_files_id"), table_name="material_files")
    op.drop_table("material_files")
