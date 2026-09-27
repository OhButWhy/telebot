from uuid import uuid4

from sqlalchemy import case, cast, delete, Float, func, or_, select, update
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
    MaterialFile,
    MaterialRating,
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
                          description: str = ""):
    material = Material(
        seller_id=seller_id,
        subject_id=subject_id,
        topic_id=topic_id,
        sort_order=sort_order,
        title=title,
        subject=subject,
        professor=professor,
        price=price,
        description=description,
        telegram_file_id=file_id,
    )
    session.add(material)
    await session.flush()
    session.add(MaterialFile(
        material_id=material.id,
        telegram_file_id=file_id,
    ))
    if topic_id:
        await change_topic_material_counts(session, topic_id, 1)
    await session.commit()
    await session.refresh(material)
    return material


async def add_material_file(session: AsyncSession, material_id: int,
                            telegram_file_id: str,
                            file_name: str | None = None):
    material_file = MaterialFile(
        material_id=material_id,
        telegram_file_id=telegram_file_id,
        file_name=file_name,
    )
    session.add(material_file)
    await session.commit()
    return material_file


async def list_subjects(session: AsyncSession):
    result = await session.execute(
        select(Subject).order_by(Subject.parent_id.asc(), Subject.name.asc())
    )
    return result.scalars().all()


async def create_topic(session: AsyncSession, subject_id: int,
                       creator_id: int, name: str,
                       parent_topic_id: int | None = None):
    topic = Topic(
        subject_id=subject_id,
        parent_topic_id=parent_topic_id,
        creator_id=creator_id,
        name=name,
    )
    session.add(topic)
    await session.commit()
    await session.refresh(topic)
    return topic


async def list_topics(session: AsyncSession, subject_id: int,
                      parent_topic_id: int | None = None,
                      limit: int = 10, offset: int = 0):
    result = await session.execute(
        select(Topic)
        .where(
            Topic.subject_id == subject_id,
            Topic.parent_topic_id == parent_topic_id,
        )
        .order_by(
            Topic.material_count.desc(),
            Topic.name.asc(),
            Topic.id.asc(),
        )
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def count_topics(session: AsyncSession, subject_id: int,
                       parent_topic_id: int | None = None) -> int:
    result = await session.execute(
        select(func.count(Topic.id)).where(
            Topic.subject_id == subject_id,
            Topic.parent_topic_id == parent_topic_id,
        )
    )
    return result.scalar_one()


async def get_topic(session: AsyncSession, topic_id: int):
    result = await session.execute(select(Topic).where(Topic.id == topic_id))
    return result.scalars().first()


async def change_topic_material_counts(session: AsyncSession, topic_id: int,
                                       delta: int):
    """Bump a topic and all its ancestors, without committing.

    Callers keep this inside the same transaction as the material change so
    the counters can never drift from the actual rows.
    """
    current_id = topic_id
    seen = set()
    while current_id and current_id not in seen:
        seen.add(current_id)
        result = await session.execute(
            update(Topic)
            .where(Topic.id == current_id)
            .values(material_count=case(
                (Topic.material_count + delta < 0, 0),
                else_=Topic.material_count + delta,
            ))
            .returning(Topic.parent_topic_id)
        )
        row = result.first()
        if row is None:
            break
        current_id = row[0]


async def get_subject(session: AsyncSession, subject_id: int):
    result = await session.execute(
        select(Subject).where(Subject.id == subject_id)
    )
    return result.scalars().first()


def _material_filters(university: str, search_term: str | None,
                      subject_id: int | None, topic_id: int | None):
    filters = [
        User.university == university,
    ]
    if search_term:
        pattern = f"%{search_term}%"
        filters.append(or_(
            Material.title.ilike(pattern),
            Material.subject.ilike(pattern),
            Material.professor.ilike(pattern),
        ))
    if subject_id is not None:
        filters.append(Material.subject_id == subject_id)
    if topic_id == -1:
        filters.append(Material.topic_id.is_(None))
    elif topic_id is not None:
        filters.append(Material.topic_id == topic_id)
    return filters


async def count_materials(session: AsyncSession, university: str,
                          search_term: str | None = None,
                          subject_id: int | None = None,
                          topic_id: int | None = None) -> int:
    result = await session.execute(
        select(func.count(Material.id))
        .join(Material.seller)
        .where(*_material_filters(
            university, search_term, subject_id, topic_id,
        ))
    )
    return result.scalar_one()


async def list_materials(session: AsyncSession, university: str,
                         search_term: str | None = None,
                         subject_id: int | None = None,
                         topic_id: int | None = None,
                         limit: int = 10, offset: int = 0):
    filters = _material_filters(university, search_term, subject_id, topic_id)
    thanks = (
        select(func.count(MaterialRating.id))
        .where(
            MaterialRating.material_id == Material.id,
            MaterialRating.value == "thanks",
        )
        .scalar_subquery()
    )
    not_ouch = (
        select(func.count(MaterialRating.id))
        .where(
            MaterialRating.material_id == Material.id,
            MaterialRating.value == "not_ouch",
        )
        .scalar_subquery()
    )
    rating_score = cast(thanks, Float) / (cast(not_ouch, Float) + 1.0)
    query = (
        select(Material)
        .options(
            selectinload(Material.seller),
            selectinload(Material.subject_ref),
        )
        .join(Material.seller)
        .where(*filters)
        .order_by(
            rating_score.desc(),
            Material.sort_order.desc(),
            Material.created_at.desc(),
            Material.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(query)
    return result.scalars().all()


async def save_material_rating(session: AsyncSession, material_id: int,
                               user_id: int, value: str):
    result = await session.execute(
        select(MaterialRating).where(
            MaterialRating.material_id == material_id,
            MaterialRating.user_id == user_id,
        )
    )
    rating = result.scalars().first()
    if rating:
        rating.value = value
    else:
        rating = MaterialRating(
            material_id=material_id,
            user_id=user_id,
            value=value,
        )
        session.add(rating)
    await session.commit()
    return rating


async def get_material(session: AsyncSession, material_id: int):
    result = await session.execute(
        select(Material)
        .options(
            selectinload(Material.seller),
            selectinload(Material.files),
            selectinload(Material.subject_ref),
        )
        .where(Material.id == material_id)
    )
    return result.scalars().first()


async def list_user_materials(session: AsyncSession, seller_id: int,
                              limit: int | None = None,
                              offset: int = 0):
    query = (
        select(Material)
        .where(Material.seller_id == seller_id)
        .order_by(Material.created_at.desc(), Material.id.desc())
    )
    if limit is not None:
        query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    return result.scalars().all()


async def count_user_materials(session: AsyncSession, seller_id: int) -> int:
    result = await session.execute(
        select(func.count(Material.id)).where(Material.seller_id == seller_id)
    )
    return result.scalar_one()


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


async def get_user_transaction_for_material(session: AsyncSession,
                                            material_id: int, user_id: int):
    result = await session.execute(
        select(Transaction).where(
            Transaction.material_id == material_id,
            Transaction.buyer_id == user_id,
        )
    )
    return result.scalars().first()


async def list_user_transactions(session: AsyncSession, buyer_id: int,
                                 limit: int | None = None,
                                 offset: int = 0):
    query = (
        select(Transaction)
        .options(selectinload(Transaction.material))
        .where(Transaction.buyer_id == buyer_id)
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
    )
    if limit is not None:
        query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    return result.scalars().all()


async def count_user_transactions(session: AsyncSession, buyer_id: int) -> int:
    result = await session.execute(
        select(func.count(Transaction.id)).where(
            Transaction.buyer_id == buyer_id
        )
    )
    return result.scalar_one()


async def list_seller_sales(session: AsyncSession, seller_id: int,
                            limit: int | None = None, offset: int = 0):
    """Transactions for the seller's materials, newest first."""
    query = (
        select(Transaction)
        .join(Transaction.material)
        .options(
            selectinload(Transaction.material),
            selectinload(Transaction.buyer),
        )
        .where(Material.seller_id == seller_id)
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
    )
    if limit is not None:
        query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    return result.scalars().all()


async def count_seller_sales(session: AsyncSession, seller_id: int) -> int:
    result = await session.execute(
        select(func.count(Transaction.id))
        .join(Transaction.material)
        .where(Material.seller_id == seller_id)
    )
    return result.scalar_one()


async def list_user_chats(session: AsyncSession, user_id: int,
                          limit: int | None = None, offset: int = 0):
    """Every conversation the user takes part in, most recent first."""
    latest = (
        select(
            ContactThread.id.label("thread_id"),
            func.max(ChatMessage.id).label("last_id"),
        )
        .join(ContactThread.messages)
        .where(
            (ContactThread.buyer_id == user_id)
            | (ContactThread.seller_id == user_id),
        )
        .group_by(ContactThread.id)
        .subquery()
    )
    query = (
        select(ContactThread)
        .join(latest, latest.c.thread_id == ContactThread.id)
        .options(
            selectinload(ContactThread.material).selectinload(Material.seller),
            selectinload(ContactThread.messages),
        )
        .order_by(latest.c.last_id.desc())
    )
    if limit is not None:
        query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    return result.scalars().all()


async def count_user_chats(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.count(func.distinct(ContactThread.id)))
        .join(ContactThread.messages)
        .where(
            (ContactThread.buyer_id == user_id)
            | (ContactThread.seller_id == user_id),
        )
    )
    return result.scalar_one()


async def unread_counts_by_thread(session: AsyncSession,
                                  user_id: int) -> dict[int, int]:
    """Unread incoming messages per thread, keyed by thread id."""
    result = await session.execute(
        select(ChatMessage.contact_thread_id, func.count(ChatMessage.id))
        .where(
            ChatMessage.is_read.is_(False),
            ChatMessage.sender_id != user_id,
        )
        .group_by(ChatMessage.contact_thread_id)
    )
    return {thread_id: count for thread_id, count in result.all()}


async def mark_thread_read(session: AsyncSession, thread_id: int,
                           user_id: int):
    """Mark incoming messages of the thread as read for this user."""
    await session.execute(
        update(ChatMessage)
        .where(
            ChatMessage.contact_thread_id == thread_id,
            ChatMessage.sender_id != user_id,
            ChatMessage.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await session.commit()


async def create_chat_message(
    session: AsyncSession,
    contact_thread_id: int,
    sender_id: int,
    text: str,
):
    chat_message = ChatMessage(
        contact_thread_id=contact_thread_id,
        sender_id=sender_id,
        text=text,
    )
    session.add(chat_message)
    await session.commit()
    await session.refresh(chat_message)
    return chat_message


async def delete_user_account(session: AsyncSession, tg_id: str):
    user = await get_user_by_tg(session, tg_id)
    if not user:
        return False

    await _delete_materials_by_seller(session, user.id)
    user.tg_id = f"deleted_{uuid4().hex}"
    user.username = None
    user.university = "Удалённый пользователь"
    user.faculty = None
    user.course = None
    await session.commit()
    return True


async def _delete_materials_by_seller(session: AsyncSession, seller_id: int):
    """Hard-delete a seller's materials and fix affected topic counts.

    Uses SQL DELETE so the database-owned ON DELETE CASCADE removes the
    dependent files, transactions, reports, ratings and threads.
    """
    topic_rows = await session.execute(
        select(Material.topic_id)
        .where(Material.seller_id == seller_id, Material.topic_id.is_not(None))
    )
    per_topic: dict[int, int] = {}
    for topic_id, in topic_rows.all():
        per_topic[topic_id] = per_topic.get(topic_id, 0) + 1
    result = await session.execute(
        delete(Material).where(Material.seller_id == seller_id)
    )
    for topic_id, amount in per_topic.items():
        await change_topic_material_counts(session, topic_id, -amount)
    await session.commit()
    return result.rowcount


async def delete_material(session: AsyncSession, material_id: int,
                          seller_id: int):
    material = await session.get(Material, material_id)
    if not material or material.seller_id != seller_id:
        return False
    result = await session.execute(
        delete(Material).where(
            Material.id == material_id,
            Material.seller_id == seller_id,
        )
    )
    if result.rowcount and material.topic_id:
        await change_topic_material_counts(session, material.topic_id, -1)
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
