"""replace subject seed data with the fixed catalog

Revision ID: e04b7c91d632
Revises: d92e6f14a730
Create Date: 2026-09-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e04b7c91d632"
down_revision: Union[str, Sequence[str], None] = "d92e6f14a730"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE materials SET subject_id = NULL "
            "WHERE subject_id IN (4, 5)"
        )
    )
    subjects = sa.table(
        "subjects",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("parent_id", sa.Integer()),
    )
    op.execute(
        subjects.update()
        .where(subjects.c.id.in_([1, 2, 3]))
        .values(name=sa.case(
            (subjects.c.id == 1, "__subject_math"),
            (subjects.c.id == 2, "__subject_computer"),
            else_="__subject_physics",
        ))
    )
    op.execute(
        subjects.update()
        .where(subjects.c.id == 1)
        .values(name="Математика", parent_id=None)
    )
    op.execute(
        subjects.update()
        .where(subjects.c.id == 2)
        .values(name="Компьютерные науки", parent_id=None)
    )
    op.execute(
        subjects.update()
        .where(subjects.c.id == 3)
        .values(name="Физика", parent_id=None)
    )
    op.execute(subjects.delete().where(subjects.c.id.in_([4, 5])))
    op.bulk_insert(subjects, [
        {"id": 6, "name": "История", "parent_id": None},
        {"id": 7, "name": "Биология", "parent_id": None},
        {"id": 8, "name": "Химия", "parent_id": None},
        {"id": 9, "name": "Экономика", "parent_id": None},
    ])
    op.alter_column("chat_messages", "transaction_id", nullable=True)
    op.add_column(
        "chat_messages",
        sa.Column("contact_thread_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_chat_messages_contact_thread",
        "chat_messages",
        "contact_threads",
        ["contact_thread_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_chat_messages_contact_thread_id",
        "chat_messages",
        ["contact_thread_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_chat_messages_contact_thread_id",
        table_name="chat_messages",
    )
    op.drop_constraint(
        "fk_chat_messages_contact_thread",
        "chat_messages",
        type_="foreignkey",
    )
    op.drop_column("chat_messages", "contact_thread_id")
    op.alter_column("chat_messages", "transaction_id", nullable=False)
    subjects = sa.table(
        "subjects",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("parent_id", sa.Integer()),
    )
    op.execute(subjects.delete().where(subjects.c.id.in_([6, 7, 8, 9])))
    op.execute(
        subjects.update()
        .where(subjects.c.id == 1)
        .values(name="Физика", parent_id=None)
    )
    op.execute(
        subjects.update()
        .where(subjects.c.id == 2)
        .values(name="Математика", parent_id=None)
    )
    op.execute(
        subjects.update()
        .where(subjects.c.id == 3)
        .values(name="Программирование", parent_id=None)
    )
    op.bulk_insert(subjects, [
        {"id": 4, "name": "Статистическая физика", "parent_id": 3},
        {
            "id": 5,
            "name": "Физика конденсированного состояния",
            "parent_id": 3,
        },
    ])
