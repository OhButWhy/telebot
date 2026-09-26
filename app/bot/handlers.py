import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from app.db.session import async_session_maker
from app.db.queries import get_user_by_tg, create_user, create_material

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    logger.info("START HANDLER: received /start from %s", message.from_user.id)
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(message.from_user.id))
        if not user:
            await create_user(
                session=session,
                tg_id=str(message.from_user.id),
                username=message.from_user.username,
                university="Unknown",
                faculty=None,
                course=None,
            )
            logger.info("Created new user %s", message.from_user.id)
            await message.answer(
                f"Привет, {message.from_user.first_name}!"
            )
        else:
            logger.info("Existing user %s", message.from_user.id)
            await message.answer("Привет! Ты уже в системе.")


@router.message(F.document)
async def handle_document(message: Message):
    logger.info("DOCUMENT HANDLER: from %s", message.from_user.id)
    async with async_session_maker() as session:
        seller = await get_user_by_tg(session, str(message.from_user.id))
        if not seller:
            await message.answer("Сначала нажми /start, для регистрации!")
            return
        material = await create_material(
            session=session,
            seller_id=seller.id,
            title=message.document.file_name,
            price=100.0,
            file_id=message.document.file_id,
        )
        logger.info("Created material id=%s", material.id)
        await message.answer(
            f"* Материал «{material.title}» добавлен!\n"
            f"ID в базе: {material.id}\nЦена: {material.price:.0f} ₽"
        )
