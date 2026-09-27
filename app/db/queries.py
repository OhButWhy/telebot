from uuid import uuid4

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models import (
    ChatMessage,
    ContactThread,
    Material,
    Report,
    Subject,
    Topic,
    Transaction,
    User,
)


async def get_user_by_tg(session: AsyncSession, tg_id: str):
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    return result.scalars().first()


async def get_user_by_id(session: AsyncSession, user_id: int):
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def create_user(session: AsyncSession, tg_id: str, username: str | None,
                      university: str, faculty: str | None,
                      course: int | None):
    user = User(
        tg_id=tg_id,
        username=username,
        university=university,
        faculty=faculty,
        course=course
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user_profile(session: AsyncSession, user: User,
                              university: str, faculty: str, course: int):
    user.university = university
    user.faculty = faculty
    user.course = course
    await session.commit()
    await session.refresh(user)
    return user


async def create_material(session: AsyncSession, seller_id: int,
                          title: str, price: float, file_id: str,
                          subject_id: int | None = None,
                          topic_id: int | None = None,
                          sort_order: int = 0,
                          subject: str = "Разное",
                          professor: str = "Не указан",
                          work_type: str = "Документ",
                          description: str = ""):
    material = Material(
        seller_id=seller_id,
        subject_id=subject_id,
        topic_id=topic_id,
        sort_order=sort_order,
        title=title,
        subject=subject,
        professor=professor,
        work_type=work_type,
        price=price,
        description=description,
        telegram_file_id=file_id,
        status="active"
    )
    session.add(material)
    await session.commit()
    await session.refresh(material)
    return material


async def list_subjects(session: AsyncSession):
    result = await session.execute(
        select(Subject).order_by(Subject.parent_id.asc(), Subject.name.asc())
    )
    return result.scalars().all()


async def create_topic(session: AsyncSession, subject_id: int,
                       creator_id: int, name: str):
    topic = Topic(
        subject_id=subject_id,
        creator_id=creator_id,
        name=name,
    )
    session.add(topic)
    await session.commit()
    await session.refresh(topic)
    return topic


async def list_topics(session: AsyncSession, subject_id: int):
    result = await session.execute(
        select(Topic)
        .where(Topic.subject_id == subject_id)
        .order_by(Topic.name.asc(), Topic.id.asc())
    )
    return result.scalars().all()


async def get_subject(session: AsyncSession, subject_id: int):
    result = await session.execute(
        select(Subject).where(Subject.id == subject_id)
    )
    return result.scalars().first()


async def list_materials(session: AsyncSession, university: str,
                         search_term: str | None = None,
                         limit: int = 10, offset: int = 0):
    filters = [
        User.university == university,
        Material.status == "active",
    ]
    if search_term:
        pattern = f"%{search_term}%"
        filters.append(or_(
            Material.title.ilike(pattern),
            Material.subject.ilike(pattern),
            Material.professor.ilike(pattern),
        ))
    query = (
        select(Material)
        .join(Material.seller)
        .where(*filters)
        .order_by(
            Material.sort_order.desc(),
            Material.created_at.desc(),
            Material.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(query)
    return result.scalars().all()


async def get_material(session: AsyncSession, material_id: int):
    result = await session.execute(
        select(Material)
        .options(selectinload(Material.seller))
        .where(Material.id == material_id)
    )
    return result.scalars().first()


async def list_user_materials(session: AsyncSession, seller_id: int):
    result = await session.execute(
        select(Material)
        .where(Material.seller_id == seller_id)
        .order_by(Material.created_at.desc(), Material.id.desc())
    )
    return result.scalars().all()


async def get_or_create_transaction(session: AsyncSession, material_id: int,
                                    buyer_id: int):
    result = await session.execute(
        select(Transaction).where(
            Transaction.material_id == material_id,
            Transaction.buyer_id == buyer_id,
        )
    )
    transaction = result.scalars().first()
    if transaction:
        return transaction

    transaction = Transaction(
        material_id=material_id,
        buyer_id=buyer_id,
        status="delivered",
        amount=0,
    )
    session.add(transaction)
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def list_user_transactions(session: AsyncSession, buyer_id: int):
    result = await session.execute(
        select(Transaction)
        .options(selectinload(Transaction.material))
        .where(Transaction.buyer_id == buyer_id)
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
    )
    return result.scalars().all()


async def list_user_chats(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(Transaction)
        .options(selectinload(Transaction.material))
        .join(Transaction.material)
        .where(
            (Transaction.buyer_id == user_id)
            | (Material.seller_id == user_id),
        )
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
    )
    return result.scalars().all()


async def get_transaction_for_user(session: AsyncSession,
                                   transaction_id: int, user_id: int):
    result = await session.execute(
        select(Transaction)
        .options(
            selectinload(Transaction.material).selectinload(Material.seller),
        )
        .where(
            Transaction.id == transaction_id,
            (Transaction.buyer_id == user_id)
            | (Material.seller_id == user_id),
        )
        .join(Transaction.material)
    )
    return result.scalars().first()


async def create_chat_message(
    session: AsyncSession,
    transaction_id: int | None,
    sender_id: int,
    text: str,
    contact_thread_id: int | None = None,
):
    chat_message = ChatMessage(
        transaction_id=transaction_id,
        contact_thread_id=contact_thread_id,
        sender_id=sender_id,
        text=text,
    )
    session.add(chat_message)
    await session.commit()
    await session.refresh(chat_message)
    return chat_message


async def list_chat_messages(session: AsyncSession, transaction_id: int):
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.transaction_id == transaction_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
    )
    return result.scalars().all()


async def delete_user_account(session: AsyncSession, tg_id: str):
    user = await get_user_by_tg(session, tg_id)
    if not user:
        return False

    await session.execute(
        update(Material)
        .where(Material.seller_id == user.id)
        .values(status="deleted")
    )
    user.tg_id = f"deleted_{uuid4().hex}"
    user.username = None
    user.university = "Удалённый пользователь"
    user.faculty = None
    user.course = None
    await session.commit()
    return True


async def delete_material(session: AsyncSession, material_id: int,
                          seller_id: int):
    result = await session.execute(
        update(Material)
        .where(
            Material.id == material_id,
            Material.seller_id == seller_id,
            Material.status == "active",
        )
        .values(status="deleted")
    )
    await session.commit()
    return result.rowcount > 0


async def update_material(session: AsyncSession, material_id: int,
                          seller_id: int, **values):
    result = await session.execute(
        update(Material)
        .where(Material.id == material_id, Material.seller_id == seller_id)
        .values(**values)
    )
    await session.commit()
    return result.rowcount > 0


async def get_or_create_contact_thread(session: AsyncSession, material_id: int,
                                       buyer_id: int, seller_id: int):
    result = await session.execute(
        select(ContactThread).where(
            ContactThread.material_id == material_id,
            ContactThread.buyer_id == buyer_id,
            ContactThread.seller_id == seller_id,
        )
    )
    thread = result.scalars().first()
    if thread:
        return thread
    thread = ContactThread(
        material_id=material_id,
        buyer_id=buyer_id,
        seller_id=seller_id,
    )
    session.add(thread)
    await session.commit()
    await session.refresh(thread)
    return thread


async def create_report(session: AsyncSession, material_id: int,
                        reporter_id: int, comment: str):
    report = Report(
        material_id=material_id,
        reporter_id=reporter_id,
        comment=comment,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


async def get_contact_thread_for_user(session: AsyncSession, thread_id: int,
                                      user_id: int):
    result = await session.execute(
        select(ContactThread)
        .options(selectinload(ContactThread.material))
        .where(
            ContactThread.id == thread_id,
            (ContactThread.buyer_id == user_id)
            | (ContactThread.seller_id == user_id),
        )
    )
    return result.scalars().first()


async def list_contact_messages(session: AsyncSession, thread_id: int):
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.contact_thread_id == thread_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
    )
    return result.scalars().all()
