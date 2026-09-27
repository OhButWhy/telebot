import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.bot.common import PAGE_SIZE
from app.bot.keyboards import author_name, catalog_keyboard
from app.bot.states import SearchState
from app.db.queries import count_materials, get_user_by_tg, list_materials
from app.db.session import async_session_maker

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("catalog"))
async def cmd_catalog(message: Message):
    search_term = None
    if message.text and " " in message.text:
        search_term = message.text.split(" ", 1)[1].strip() or None
    await send_catalog(message, search_term=search_term)


@router.message(Command("search"))
async def cmd_search(message: Message):
    if not message.text or " " not in message.text:
        await message.answer(
            "Используй команду так: /search название предмета"
        )
        return
    search_term = message.text.split(" ", 1)[1].strip()
    if not search_term:
        await message.answer("Напиши текст для поиска после команды /search.")
        return
    await send_catalog(message, search_term=search_term)


@router.message(SearchState.waiting_query, F.text)
async def search_query(message: Message, state: FSMContext):
    search_term = message.text.strip()
    if not search_term:
        await message.answer("Введи непустой поисковый запрос.")
        return
    await state.clear()
    await send_catalog(message, search_term=search_term)


async def send_catalog(message: Message, search_term: str | None = None,
                       offset: int = 0, telegram_user_id: int | None = None):
    user_id = telegram_user_id or message.from_user.id
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(user_id))
        if not user:
            await message.answer("Сначала нажми /start, для регистрации!")
            return
        materials = await list_materials(
            session,
            user.university,
            search_term=search_term,
            limit=PAGE_SIZE + 1,
            offset=offset,
        )
        total = await count_materials(
            session, user.university, search_term=search_term
        )

    if not materials:
        text = "Поиск ничего не нашёл." if search_term else (
            "В каталоге пока нет материалов для твоего вуза."
        )
        await message.answer(text)
        return

    has_next = len(materials) > PAGE_SIZE
    lines = [f"🔍 Найдено: {total}", ""]
    rows: list[list] = []
    for index, material in enumerate(materials[:PAGE_SIZE], start=1):
        author = author_name(material)
        lines.append(
            f"{index + offset}. {material.title} — {material.price:.0f} ₽ "
            f"(by {author})"
        )
        rows.append([InlineKeyboardButton(
            text=f"📄 {material.title} — {material.price:.0f} ₽",
            callback_data=f"material:{material.id}",
        )])
    page_keyboard = catalog_keyboard(offset, has_next, search_term)
    if page_keyboard:
        rows.extend(page_keyboard.inline_keyboard)
    await message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("catalog:"))
async def catalog_page(callback: CallbackQuery):
    parts = callback.data.split(":", 2)
    offset = int(parts[1])
    search_term = parts[2] if len(parts) == 3 else None
    await callback.answer()
    await send_catalog(
        callback.message,
        search_term=search_term,
        offset=offset,
        telegram_user_id=callback.from_user.id,
    )

