import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import delete_account_keyboard
from app.db.queries import (
    delete_material,
    delete_user_account,
    get_user_by_tg,
)
from app.db.session import async_session_maker

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("delete_account"))
async def cmd_delete_account(message: Message):
    await message.answer(
        "Аккаунт будет обезличен, а все твои материалы и связанные с ними "
        "история получений, рейтинги и чаты будут безвозвратно удалены.\n\n"
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


@router.callback_query(F.data == "delete_material:cancel")
async def cancel_delete_material(callback: CallbackQuery):
    await callback.answer("Удаление отменено")
    await callback.message.edit_text("Удаление материала отменено.")


@router.callback_query(F.data.startswith("delete_material:confirm:"))
async def confirm_delete_material(callback: CallbackQuery):
    material_id = int(callback.data.rsplit(":", 1)[1])
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(callback.from_user.id))
        deleted = bool(user) and await delete_material(
            session,
            material_id,
            user.id,
        )
    if not deleted:
        await callback.answer("Материал уже удалён или недоступен.",
                              show_alert=True)
        return
    await callback.answer("Материал удалён")
    await callback.message.edit_text("Материал удалён из каталога.")

