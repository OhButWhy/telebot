"""add canonical subject directory

Revision ID: c31a5e8b204f
Revises: 8f2c1d7e9a10
Create Date: 2026-09-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c31a5e8b204f"
down_revision: Union[str, Sequence[str], None] = "8f2c1d7e9a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["subjects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_subjects_id"), "subjects", ["id"], unique=False)
    op.add_column(
        "materials",
        sa.Column("subject_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_materials_subject_id",
        "materials",
        "subjects",
        ["subject_id"],
        ["id"],
    )
    subjects = sa.table(
        "subjects",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("parent_id", sa.Integer()),
    )
    op.bulk_insert(subjects, [
        {"id": 1, "name": "Физика", "parent_id": None},
        {"id": 2, "name": "Математика", "parent_id": None},
        {"id": 3, "name": "Программирование", "parent_id": None},
        {"id": 4, "name": "Статистическая физика", "parent_id": 1},
        {
            "id": 5,
            "name": "Физика конденсированного состояния",
            "parent_id": 1,
        },
    ])


def downgrade() -> None:
    op.drop_constraint(
        "fk_materials_subject_id",
        "materials",
        type_="foreignkey",
    )
    op.drop_column("materials", "subject_id")
    op.drop_index(op.f("ix_subjects_id"), table_name="subjects")
    op.drop_table("subjects")
