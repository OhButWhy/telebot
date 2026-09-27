import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.account import cmd_delete_account
from app.bot.catalog import show_subjects
from app.bot.mylists import cmd_my_chats, cmd_my_materials, cmd_my_purchases
from app.bot.profile import edit_profile
from app.bot.states import SearchState
from app.bot.upload import start_upload

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "Каталог")
async def menu_catalog(message: Message):
    await show_subjects(message)


@router.message(F.text == "Поиск")
async def menu_search(message: Message, state: FSMContext):
    await state.set_state(SearchState.waiting_query)
    await message.answer("Введи название, предмет или преподавателя:")


@router.message(F.text == "Загрузить")
async def menu_upload(message: Message, state: FSMContext):
    await start_upload(message, state)


@router.message(F.text == "Мои материалы")
async def menu_my_materials(message: Message):
    await cmd_my_materials(message)


@router.message(F.text == "Мои получения")
async def menu_my_purchases(message: Message):
    await cmd_my_purchases(message)


@router.message(F.text.in_({"Профиль", "👤 Профиль", "⚙️ Профиль"}))
async def menu_profile(message: Message, state: FSMContext):
    await edit_profile(message, state)


@router.message(F.text == "Чаты")
async def menu_chats(message: Message):
    await cmd_my_chats(message)


@router.message(F.text == "Удалить аккаунт")
async def menu_delete_account(message: Message):
    await cmd_delete_account(message)

