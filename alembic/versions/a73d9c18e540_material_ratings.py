"""add material ratings

Revision ID: a73d9c18e540
Revises: f16a8c32b741
Create Date: 2026-09-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a73d9c18e540"
down_revision: Union[str, Sequence[str], None] = "f16a8c32b741"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "material_ratings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["material_id"], ["materials.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "material_id", "user_id",
            name="uq_material_ratings_material_user",
        ),
    )
    op.create_index(
        op.f("ix_material_ratings_id"),
        "material_ratings",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_material_ratings_id"),
        table_name="material_ratings",
    )
    op.drop_table("material_ratings")
