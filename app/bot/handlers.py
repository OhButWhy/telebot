from aiogram import Router, F
from aiogram.types import Message
from app.db.session import get_session
from app.db.queries import get_user_by_tg, create_user, create_material

router = Router()


@router.message(F.command == "start")
async def cmd_start(message: Message):
    async with get_session() as session:
        user = await get_user_by_tg(session, str(message.from_user.id))
        if not user:
            user = await create_user(
                session=session,
                tg_id=str(message.from_user.id),
                username=message.from_user.username,
                university="Unknown",
                faculty=None,
                course=None
            )
            await message.answer(f"Привет, {message.from_user.first_name}!")
        else:
            await message.answer("Привет! Ты уже в системе.")


@router.message(F.document)
async def handle_document(message: Message):
    async with get_session() as session:
        seller = await get_user_by_tg(session, str(message.from_user.id))
        if not seller:
            await message.answer("Сначала нажми /start, для регистрации!")
            return

        # пока фиксим 100 ₽
        material = await create_material(
            session=session,
            seller_id=seller.id,
            title=message.document.file_name,
            price=100.0,
            file_id=message.document.file_id
        )
        await message.answer(
            f"* Материал '{material.title}' добавлен!\n"
            f"ID в базе: {material.id}\n"
            f"Цена: {material.price} ₽"
        )
