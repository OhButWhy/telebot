"""unify chats on contact threads

Chats used to be stored twice: contact (pre-purchase) messages hung off a
contact thread, while purchase messages hung off a transaction. Both sides
of a conversation could therefore end up in different places. Everything
now lives on contact_threads, so a thread is the single conversation per
(material, buyer, seller).

Revision ID: e5f6a7b8c9d0
Revises: c2b3d4e5f6a7
Create Date: 2026-09-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "c2b3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Every transaction that carries messages becomes a thread.
    op.execute("""
        INSERT INTO contact_threads
            (material_id, buyer_id, seller_id, created_at)
        SELECT DISTINCT t.material_id, t.buyer_id, m.seller_id, t.created_at
        FROM transactions t
        JOIN materials m ON m.id = t.material_id
        WHERE EXISTS (
            SELECT 1 FROM chat_messages c WHERE c.transaction_id = t.id
        )
        ON CONFLICT (material_id, buyer_id, seller_id) DO NOTHING
    """)
    # Move the transaction messages onto their thread.
    op.execute("""
        UPDATE chat_messages
        SET contact_thread_id = ct.id
        FROM transactions t
        JOIN materials m ON m.id = t.material_id
        JOIN contact_threads ct
          ON ct.material_id = t.material_id
         AND ct.buyer_id = t.buyer_id
         AND ct.seller_id = m.seller_id
        WHERE chat_messages.transaction_id = t.id
          AND chat_messages.contact_thread_id IS NULL
    """)
    # Drop transaction messages that never got a thread (orphaned data).
    op.execute("DELETE FROM chat_messages WHERE contact_thread_id IS NULL")
    op.alter_column("chat_messages", "contact_thread_id", nullable=False)
    op.drop_index(
        "ix_chat_messages_transaction_id", table_name="chat_messages"
    )
    op.drop_column("chat_messages", "transaction_id")


def downgrade() -> None:
    op.alter_column("chat_messages", "contact_thread_id", nullable=True)
    op.add_column(
        "chat_messages",
        sa.Column("transaction_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_chat_messages_transaction",
        "chat_messages",
        "transactions",
        ["transaction_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_chat_messages_transaction_id"),
        "chat_messages",
        ["transaction_id"],
        unique=False,
    )
    op.execute("""
        UPDATE chat_messages
        SET transaction_id = t.id
        FROM transactions t
        JOIN contact_threads ct ON ct.material_id = t.material_id
         AND ct.buyer_id = t.buyer_id
        WHERE chat_messages.contact_thread_id = ct.id
    """)
    # Conversations that never had a transaction cannot be represented
    # in the old schema.
    op.execute("DELETE FROM chat_messages WHERE transaction_id IS NULL")
    op.alter_column("chat_messages", "transaction_id", nullable=False)
