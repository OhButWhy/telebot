"""backfill cached subtree material counts

Revision ID: d1a2b3c4d5e6
Revises: b84e1d27c630
Create Date: 2026-09-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "b84e1d27c630"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BACKFILL = """
WITH RECURSIVE topic_tree AS (
    SELECT id AS ancestor_id, id AS descendant_id
    FROM topics
    UNION ALL
    SELECT tree.ancestor_id, child.id
    FROM topic_tree AS tree
    JOIN topics AS child ON child.parent_topic_id = tree.descendant_id
)
UPDATE topics
SET material_count = COALESCE((
    SELECT COUNT(materials.id)
    FROM topic_tree
    JOIN materials
      ON materials.topic_id = topic_tree.descendant_id
    WHERE topic_tree.ancestor_id = topics.id
), 0);
"""


def upgrade() -> None:
    op.execute(BACKFILL)


def downgrade() -> None:
    op.execute("UPDATE topics SET material_count = 0")
