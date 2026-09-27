"""add topics, material ordering, contact threads and reports

Revision ID: d92e6f14a730
Revises: c31a5e8b204f
Create Date: 2026-09-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d92e6f14a730"
down_revision: Union[str, Sequence[str], None] = "c31a5e8b204f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["creator_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"], ["subjects.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_topics_id"), "topics", ["id"], unique=False)
    op.add_column(
        "materials",
        sa.Column("topic_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "materials",
        sa.Column(
            "sort_order", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.create_foreign_key(
        "fk_materials_topic_id", "materials", "topics", ["topic_id"], ["id"]
    )
    op.create_table(
        "contact_threads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["buyer_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["material_id"], ["materials.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["seller_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "material_id", "buyer_id", "seller_id",
            name="uq_contact_threads_participants",
        ),
    )
    op.create_index(
        op.f("ix_contact_threads_id"), "contact_threads", ["id"], unique=False
    )
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("reporter_id", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["material_id"], ["materials.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["reporter_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reports_id"), "reports", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reports_id"), table_name="reports")
    op.drop_table("reports")
    op.drop_index(op.f("ix_contact_threads_id"), table_name="contact_threads")
    op.drop_table("contact_threads")
    op.drop_constraint(
        "fk_materials_topic_id", "materials", type_="foreignkey"
    )
    op.drop_column("materials", "sort_order")
    op.drop_column("materials", "topic_id")
    op.drop_index(op.f("ix_topics_id"), table_name="topics")
    op.drop_table("topics")
