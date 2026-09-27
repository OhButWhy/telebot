import logging

from aiogram import Router
from aiogram.types import InlineKeyboardButton, Message

from app.bot.keyboards import MAIN_MENU
from app.db.queries import get_user_by_tg
from app.db.session import async_session_maker

logger = logging.getLogger(__name__)
router = Router()


async def show_main_menu(message: Message):
    await message.answer("Главное меню:", reply_markup=MAIN_MENU)


PAGE_SIZE = 10


def materials_word(count: int) -> str:
    tail = count % 100
    if 11 <= tail <= 14:
        return "материалов"
    last = count % 10
    if last == 1:
        return "материал"
    if last in (2, 3, 4):
        return "материала"
    return "материалов"


def nav_keyboard(subject_id: int, topic_id: int,
                 parent_topic_id: int | None = None) -> list[list]:
    rows = []
    if topic_id:
        target = parent_topic_id or 0
        rows.append([InlineKeyboardButton(
            text="⬅️ Назад в раздел",
            callback_data=f"browse_topic:{subject_id}:{target}:0",
        )])
    rows.append([InlineKeyboardButton(
        text="📚 К предметам",
        callback_data="browse_subjects",
    )])
    return rows


def _page_row(prefix: str, subject_id: int, topic_id: int,
              topics_offset: int, materials_offset: int, offset: int,
              total: int, label: str) -> list:
    buttons = []
    if offset > 0:
        buttons.append(InlineKeyboardButton(
            text=f"⬅️ {label}",
            callback_data=(
                f"{prefix}:{subject_id}:{topic_id}:"
                f"{topics_offset}:{materials_offset}:{max(0, offset - PAGE_SIZE)}"
            ),
        ))
    if offset + PAGE_SIZE < total:
        buttons.append(InlineKeyboardButton(
            text=f"{label} ➡️",
            callback_data=(
                f"{prefix}:{subject_id}:{topic_id}:"
                f"{topics_offset}:{materials_offset}:{offset + PAGE_SIZE}"
            ),
        ))
    return buttons


async def get_user_for_message(message: Message):
    async with async_session_maker() as session:
        return await get_user_by_tg(session, str(message.from_user.id))

