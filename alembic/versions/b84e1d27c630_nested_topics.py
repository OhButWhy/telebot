"""add nested topics and subtree material counts

Revision ID: b84e1d27c630
Revises: a73d9c18e540
Create Date: 2026-09-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b84e1d27c630"
down_revision: Union[str, Sequence[str], None] = "a73d9c18e540"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "topics",
        sa.Column("parent_topic_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "topics",
        sa.Column("material_count", sa.Integer(), nullable=False,
                  server_default="0"),
    )
    op.create_foreign_key(
        "fk_topics_parent_topic",
        "topics",
        "topics",
        ["parent_topic_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_topics_parent_topic",
        "topics",
        type_="foreignkey",
    )
    op.drop_column("topics", "material_count")
    op.drop_column("topics", "parent_topic_id")