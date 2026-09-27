import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.bot.common import PAGE_SIZE, _page_row, materials_word, nav_keyboard
from app.bot.keyboards import browse_subject_keyboard, topic_keyboard
from app.db.queries import (
    count_materials,
    count_topics,
    get_subject,
    get_topic,
    get_user_by_tg,
    list_materials,
    list_subjects,
    list_topics,
)
from app.db.session import async_session_maker

logger = logging.getLogger(__name__)
router = Router()



async def show_subjects(message: Message, telegram_user_id: int | None = None):
    user_id = telegram_user_id or message.from_user.id
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(user_id))
        subjects = await list_subjects(session)
    if not user:
        await message.answer("Сначала нажми /start, для регистрации!")
        return
    await message.answer(
        "Выбери предмет:",
        reply_markup=browse_subject_keyboard(subjects),
    )


async def show_catalog_page(message: Message, subject_id: int, topic_id: int = 0,
                            telegram_user_id: int | None = None,
                            topics_offset: int = 0,
                            materials_offset: int = 0):
    """Read-only catalog view: topics first, then free materials.

    topic_id == 0 shows the subject root (top-level topics + untopiced
    materials). Any other value opens that topic (child topics + its own
    materials).
    """
    user_id = telegram_user_id or message.from_user.id
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(user_id))
        subject = await get_subject(session, subject_id)
        current_topic = await get_topic(session, topic_id) if topic_id else None
        topics = await list_topics(
            session,
            subject_id,
            parent_topic_id=topic_id or None,
            limit=11,
            offset=topics_offset,
        )
        topic_total = await count_topics(
            session, subject_id, parent_topic_id=topic_id or None
        )
        materials = await list_materials(
            session,
            user.university if user else "",
            subject_id=subject_id,
            topic_id=-1 if topic_id == 0 else topic_id,
            limit=11,
            offset=materials_offset,
        )
        material_total = await count_materials(
            session,
            user.university if user else "",
            subject_id=subject_id,
            topic_id=-1 if topic_id == 0 else topic_id,
        )
    if not user or not subject:
        await message.answer("Профиль не найден. Нажми /start.")
        return

    header = (
        f"📚 {subject.name}" if topic_id == 0
        else f"📚 {subject.name} → {current_topic.name if current_topic else 'Топик'}"
    )
    lines = [header]
    rows: list[list] = []

    if topics:
        lines.append(f"\n📂 Топики ({topic_total}):")
        for index, topic in enumerate(topics[:PAGE_SIZE], start=1):
            lines.append(
                f"{index + topics_offset}. {topic.name} — "
                f"{topic.material_count} {materials_word(topic.material_count)}"
            )
            rows.append([InlineKeyboardButton(
                text=f"📂 {topic.name} ({topic.material_count})",
                callback_data=f"browse_topic:{subject_id}:{topic.id}:0",
            )])
        topic_row = _page_row(
            "browse_topics", subject_id, topic_id,
            topics_offset, materials_offset, topics_offset, topic_total,
            "Топики",
        )
        if topic_row:
            rows.append(topic_row)
    elif topic_id == 0:
        lines.append("\n📂 Топиков пока нет.")

    if materials:
        lines.append(f"\n📄 Материалы ({material_total}):")
        for index, material in enumerate(materials[:PAGE_SIZE], start=1):
            lines.append(
                f"{index + materials_offset}. {material.title} "
                f"(by {material.seller.username if material.seller else '—'})"
            )
            rows.append([InlineKeyboardButton(
                text=f"📄 {material.title} — by "
                     f"{material.seller.username if material.seller else '—'}",
                callback_data=f"material:{material.id}",
            )])
        material_row = _page_row(
            "browse_materials", subject_id, topic_id,
            topics_offset, materials_offset, materials_offset, material_total,
            "Материалы",
        )
        if material_row:
            rows.append(material_row)
    else:
        lines.append("\n📄 Материалов в этом разделе пока нет.")

    rows.extend(nav_keyboard(
        subject_id,
        topic_id,
        current_topic.parent_topic_id if current_topic else None,
    ))
    await message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data == "browse_subjects")
async def browse_subjects_callback(callback: CallbackQuery,
                                   state: FSMContext):
    await state.clear()
    await callback.answer()
    await show_subjects(callback.message, callback.from_user.id)


@router.callback_query(F.data.startswith("browse_subject:"))
async def browse_subject_callback(callback: CallbackQuery,
                                  state: FSMContext):
    subject_id = int(callback.data.split(":", 1)[1])
    await state.clear()
    await callback.answer()
    await show_catalog_page(callback.message, subject_id, 0,
                            callback.from_user.id)


@router.callback_query(F.data.startswith("browse_topic:"))
async def browse_topic_callback(callback: CallbackQuery,
                                state: FSMContext):
    parts = callback.data.split(":")
    offset = int(parts[3]) if len(parts) > 3 else 0
    await state.clear()
    await callback.answer()
    await show_catalog_page(
        callback.message,
        int(parts[1]),
        int(parts[2]),
        callback.from_user.id,
        materials_offset=offset,
    )


@router.callback_query(F.data.startswith("browse_topics:"))
async def browse_topics_page_callback(callback: CallbackQuery,
                                      state: FSMContext):
    _, subject_id, topic_id, _, materials_offset, topics_offset = (
        callback.data.split(":")
    )
    await state.clear()
    await callback.answer()
    await show_catalog_page(
        callback.message,
        int(subject_id),
        int(topic_id),
        callback.from_user.id,
        topics_offset=int(topics_offset),
        materials_offset=int(materials_offset),
    )


@router.callback_query(F.data.startswith("browse_materials:"))
async def browse_materials_page_callback(callback: CallbackQuery,
                                         state: FSMContext):
    _, subject_id, topic_id, topics_offset, _, materials_offset = (
        callback.data.split(":")
    )
    await state.clear()
    await callback.answer()
    await show_catalog_page(
        callback.message,
        int(subject_id),
        int(topic_id),
        callback.from_user.id,
        topics_offset=int(topics_offset),
        materials_offset=int(materials_offset),
    )

