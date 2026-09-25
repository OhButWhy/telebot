from sqlalchemy import Column, Integer, String, Float, \
                         DateTime, ForeignKey, Text
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
    title = Column(String, nullable=False)
    subject = Column(String, nullable=False)          # Предмет
    professor = Column(String, nullable=False)        # Преподаватель
    work_type = Column(String, nullable=False)        # конспект/лаба/курсовая
    price = Column(Float, nullable=False)             # Цена в рублях
    description = Column(Text, nullable=True)
    file_key_s3 = Column(String, nullable=False)     # Ключ файла в S3
    status = Column(String, default="active", nullable=False)  # active/deleted

    seller = relationship("User", back_populates="materials")
    transactions = relationship("Transaction", back_populates="material")

    # Полнотекстовый индекс будет добавлен через миграцию (tsvector)
    created_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

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
