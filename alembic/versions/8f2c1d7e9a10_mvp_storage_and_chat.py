"""rename Telegram file storage field and add chat support

Revision ID: 8f2c1d7e9a10
Revises: b45f728ff835
Create Date: 2026-09-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f2c1d7e9a10"
down_revision: Union[str, Sequence[str], None] = "b45f728ff835"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "materials",
        "file_key_s3",
        new_column_name="telegram_file_id",
    )
    op.create_unique_constraint(
        "uq_transactions_material_buyer",
        "transactions",
        ["material_id", "buyer_id"],
    )
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["sender_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_chat_messages_id"), "chat_messages", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_chat_messages_transaction_id"),
        "chat_messages",
        ["transaction_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_chat_messages_transaction_id"),
        table_name="chat_messages",
    )
    op.drop_index(op.f("ix_chat_messages_id"), table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_constraint(
        "uq_transactions_material_buyer", "transactions", type_="unique"
    )
    op.alter_column(
        "materials",
        "telegram_file_id",
        new_column_name="file_key_s3",
    )
