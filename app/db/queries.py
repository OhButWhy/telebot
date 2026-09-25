from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User, Material


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


async def create_material(session: AsyncSession, seller_id: int,
                          title: str, price: float, file_id: str):
    material = Material(
        seller_id=seller_id,
        title=title,
        subject="Разное",
        professor="Не указан",
        work_type="Документ",
        price=price,
        description="Загружено через бота",
        file_key_s3=file_id,  # это и есть наш file_id из Telegram
        status="active"
    )
    session.add(material)
    await session.commit()
    await session.refresh(material)
    return material
