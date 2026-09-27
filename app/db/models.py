from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # Telegram ID
    tg_id = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    university = Column(String, nullable=False)
    faculty = Column(String, nullable=True)
    course = Column(Integer, nullable=True)

    # Материалы, которые пользователь загрузил
    materials = relationship("Material", back_populates="seller")
    # Покупки пользователя
    purchases = relationship("Transaction",
                             foreign_keys="Transaction.buyer_id",
                             back_populates="buyer")

    created_at = Column(DateTime, default=datetime.utcnow)


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer,
                       ForeignKey("users.id", ondelete="CASCADE"),
                       nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    title = Column(String, nullable=False)
    subject = Column(String, nullable=False)          # Предмет
    professor = Column(String, nullable=False)        # Преподаватель
    work_type = Column(String, nullable=False)        # конспект/лаба/курсовая
    price = Column(Float, nullable=False)             # Цена в рублях
    description = Column(Text, nullable=True)
    telegram_file_id = Column(String, nullable=False)
    status = Column(String, default="active", nullable=False)  # active/deleted

    seller = relationship("User", back_populates="materials")
    subject_ref = relationship("Subject", back_populates="materials")
    topic = relationship("Topic", back_populates="materials")
    transactions = relationship("Transaction", back_populates="material")
    files = relationship(
        "MaterialFile",
        back_populates="material",
        cascade="all, delete-orphan",
    )

    # Полнотекстовый индекс будет добавлен через миграцию (tsvector)
    created_at = Column(DateTime, default=datetime.utcnow)


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)

    parent = relationship(
        "Subject",
        remote_side=[id],
        back_populates="children",
    )
    children = relationship("Subject", back_populates="parent")
    materials = relationship("Material", back_populates="subject_ref")
    topics = relationship("Topic", back_populates="subject")


class MaterialFile(Base):
    __tablename__ = "material_files"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(
        Integer,
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    telegram_file_id = Column(String, nullable=False)
    file_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    material = relationship("Material", back_populates="files")


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(
        Integer,
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_topic_id = Column(
        Integer,
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=True,
    )
    name = Column(String, nullable=False)
    material_count = Column(Integer, default=0, nullable=False)
    creator_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    subject = relationship("Subject", back_populates="topics")
    creator = relationship("User")
    parent_topic = relationship(
        "Topic",
        remote_side=[id],
        back_populates="child_topics",
    )
    child_topics = relationship("Topic", back_populates="parent_topic")
    materials = relationship("Material", back_populates="topic")


class ContactThread(Base):
    __tablename__ = "contact_threads"
    __table_args__ = (
        UniqueConstraint(
            "material_id", "buyer_id", "seller_id",
            name="uq_contact_threads_participants",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(
        Integer,
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
    )
    buyer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    seller_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    material = relationship("Material")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(
        Integer,
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
    )
    reporter_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    comment = Column(Text, nullable=False)
    status = Column(String, default="new", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class MaterialRating(Base):
    __tablename__ = "material_ratings"
    __table_args__ = (
        UniqueConstraint(
            "material_id", "user_id",
            name="uq_material_ratings_material_user",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(
        Integer,
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("material_id", "buyer_id",
                         name="uq_transactions_material_buyer"),
    )

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer,
                         ForeignKey("materials.id", ondelete="CASCADE"),
                         nullable=False)
    buyer_id = Column(Integer,
                      ForeignKey("users.id", ondelete="CASCADE"),
                      nullable=False)
    # pending/paid/cancelled
    status = Column(String, default="pending", nullable=False)
    payment_id = Column(String, nullable=True)  # ID платежа в ЮKassa
    amount = Column(Float, nullable=False)

    material = relationship("Material", back_populates="transactions")
    buyer = relationship("User",
                         foreign_keys=[buyer_id], back_populates="purchases")

    created_at = Column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(
        Integer,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    contact_thread_id = Column(
        Integer,
        ForeignKey("contact_threads.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    sender_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    text = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
