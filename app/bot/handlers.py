import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from app.db.session import async_session_maker
from app.db.queries import (
    create_material,
    create_user,
    delete_user_account,
    get_material,
    get_or_create_transaction,
    get_user_by_tg,
    list_materials,
)

logger = logging.getLogger(__name__)
router = Router()


def material_keyboard(material_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Получить материал",
            callback_data=f"get_material:{material_id}",
        ),
    ]])


def delete_account_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Да, удалить аккаунт",
            callback_data="delete_account:confirm",
        ),
        InlineKeyboardButton(
            text="Отмена",
            callback_data="delete_account:cancel",
        ),
    ]])


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


@router.message(Command("catalog"))
async def cmd_catalog(message: Message):
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(message.from_user.id))
        if not user:
            await message.answer("Сначала нажми /start, для регистрации!")
            return
        materials = await list_materials(session, user.university)

    if not materials:
        await message.answer("В каталоге пока нет материалов для твоего вуза.")
        return

    for material in materials:
        await message.answer(
            f"{material.title}\n"
            f"Предмет: {material.subject}\n"
            f"Преподаватель: {material.professor}\n"
            f"Цена: {material.price:.0f} ₽",
            reply_markup=material_keyboard(material.id),
        )


@router.message(Command("delete_account"))
async def cmd_delete_account(message: Message):
    await message.answer(
        "Аккаунт будет обезличен, а твои материалы станут недоступны. "
        "История получений и чатов сохранится без персональных данных.\n\n"
        "Подтвердить удаление?",
        reply_markup=delete_account_keyboard(),
    )


@router.callback_query(F.data == "delete_account:cancel")
async def cancel_delete_account(callback: CallbackQuery):
    await callback.answer("Удаление отменено")
    await callback.message.edit_text("Удаление аккаунта отменено.")


@router.callback_query(F.data == "delete_account:confirm")
async def confirm_delete_account(callback: CallbackQuery):
    async with async_session_maker() as session:
        deleted = await delete_user_account(
            session,
            str(callback.from_user.id),
        )

    if not deleted:
        await callback.answer("Аккаунт уже удалён.", show_alert=True)
        return

    await callback.answer("Аккаунт удалён")
    await callback.message.edit_text(
        "Аккаунт удалён. Чтобы зарегистрироваться снова, нажми /start."
    )


@router.callback_query(F.data.startswith("get_material:"))
async def get_material_callback(callback: CallbackQuery):
    material_id = int(callback.data.split(":", 1)[1])
    async with async_session_maker() as session:
        buyer = await get_user_by_tg(session, str(callback.from_user.id))
        material = await get_material(session, material_id)
        if not buyer or not material or material.status != "active":
            await callback.answer("Материал недоступен.", show_alert=True)
            return
        if material.seller_id == buyer.id:
            await callback.answer("Нельзя получить собственный материал.",
                                  show_alert=True)
            return
        if material.seller.university != buyer.university:
            await callback.answer("Материал недоступен для твоего вуза.",
                                  show_alert=True)
            return
        await get_or_create_transaction(session, material.id, buyer.id)

    await callback.message.bot.send_document(
        chat_id=callback.from_user.id,
        document=material.telegram_file_id,
    )
    await callback.answer("Материал отправлен")
