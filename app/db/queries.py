from uuid import uuid4

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models import Material, Transaction, User


async def get_user_by_tg(session: AsyncSession, tg_id: str):
    result = await session.execute(select(User).where(User.tg_id == tg_id))
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
                          subject: str = "Разное",
                          professor: str = "Не указан",
                          work_type: str = "Документ",
                          description: str = ""):
    material = Material(
        seller_id=seller_id,
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
        .order_by(Material.created_at.desc(), Material.id.desc())
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
