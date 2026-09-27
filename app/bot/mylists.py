import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import (
    chat_keyboard,
    edit_material_keyboard,
    list_nav_keyboard,
    material_caption,
)
from app.bot.states import ChatState
from app.db.queries import (
    count_seller_sales,
    count_user_chats,
    count_user_materials,
    count_user_transactions,
    create_chat_message,
    get_contact_thread_for_user,
    get_material,
    get_or_create_contact_thread,
    get_user_by_id,
    get_user_by_tg,
    list_contact_messages,
    list_seller_sales,
    list_user_chats,
    list_user_materials,
    list_user_transactions,
    mark_thread_read,
    unread_counts_by_thread,
)
from app.db.session import async_session_maker

logger = logging.getLogger(__name__)
router = Router()

MY_PAGE_SIZE = 5


async def render_my_materials(message: Message, telegram_user_id: int,
                              offset: int = 0):
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(telegram_user_id))
        if not user:
            await message.answer("Сначала нажми /start, для регистрации!")
            return
        materials = await list_user_materials(
            session, user.id, limit=MY_PAGE_SIZE, offset=offset
        )
        total = await count_user_materials(session, user.id)

    if not materials:
        await message.answer("Ты ещё не загрузил материалы.")
        return
    for material in materials:
        await message.answer(
            material_caption(material, with_author=False),
            reply_markup=edit_material_keyboard(material.id),
        )
    nav = list_nav_keyboard(
        "my_materials", offset, total, MY_PAGE_SIZE
    )
    if nav:
        await message.answer(
            f"Материалы: {offset + 1}–{offset + len(materials)} из {total}",
            reply_markup=nav,
        )


async def render_my_purchases(message: Message, telegram_user_id: int,
                              offset: int = 0):
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(telegram_user_id))
        if not user:
            await message.answer("Сначала нажми /start, для регистрации!")
            return
        transactions = await list_user_transactions(
            session, user.id, limit=MY_PAGE_SIZE, offset=offset
        )
        total = await count_user_transactions(session, user.id)
        threads = []
        for transaction in transactions:
            material = transaction.material
            thread = await get_or_create_contact_thread(
                session, material.id, user.id, material.seller_id
            )
            threads.append((material, thread))

    if not threads:
        await message.answer("Ты ещё не получал материалы.")
        return
    for material, thread in threads:
        await message.answer(
            f"Получен материал: {material.title}",
            reply_markup=chat_keyboard(thread.id, "💬 Написать продавцу"),
        )
    nav = list_nav_keyboard(
        "my_purchases", offset, total, MY_PAGE_SIZE
    )
    if nav:
        await message.answer(
            f"Получения: {offset + 1}–{offset + len(threads)} из {total}",
            reply_markup=nav,
        )


async def render_my_chats(message: Message, telegram_user_id: int,
                          offset: int = 0):
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(telegram_user_id))
        if not user:
            await message.answer("Сначала нажми /start, для регистрации!")
            return
        threads = await list_user_chats(
            session, user.id, limit=MY_PAGE_SIZE, offset=offset
        )
        total = await count_user_chats(session, user.id)
        unread = await unread_counts_by_thread(session, user.id)

    if not threads:
        await message.answer("У тебя пока нет чатов.")
        return
    for thread in threads:
        last = thread.messages[-1]
        preview = last.text.replace("\n", " ")
        if len(preview) > 60:
            preview = preview[:60] + "…"
        badge = unread.get(thread.id)
        title = f"💬 {thread.material.title}"
        if badge:
            title += f" 🔴 {badge}"
        await message.answer(
            f"{title}\n"
            f"{'Ты' if last.sender_id == user.id else 'Собеседник'}: "
            f"{preview}",
            reply_markup=chat_keyboard(thread.id),
        )
    nav = list_nav_keyboard("my_chats", offset, total, MY_PAGE_SIZE)
    if nav:
        await message.answer(
            f"Чаты: {offset + 1}–{offset + len(threads)} из {total}",
            reply_markup=nav,
        )


@router.message(Command("my_materials"))
async def cmd_my_materials(message: Message):
    await render_my_materials(message, message.from_user.id)


@router.message(Command("my_purchases"))
async def cmd_my_purchases(message: Message):
    await render_my_purchases(message, message.from_user.id)


@router.message(Command("my_chats"))
async def cmd_my_chats(message: Message):
    await render_my_chats(message, message.from_user.id)


@router.callback_query(F.data.startswith("my_materials:"))
async def my_materials_page(callback: CallbackQuery):
    offset = int(callback.data.split(":", 1)[1])
    await callback.answer()
    await render_my_materials(callback.message, callback.from_user.id, offset)


@router.callback_query(F.data.startswith("my_purchases:"))
async def my_purchases_page(callback: CallbackQuery):
    offset = int(callback.data.split(":", 1)[1])
    await callback.answer()
    await render_my_purchases(callback.message, callback.from_user.id, offset)


@router.callback_query(F.data.startswith("my_chats:"))
async def my_chats_page(callback: CallbackQuery):
    offset = int(callback.data.split(":", 1)[1])
    await callback.answer()
    await render_my_chats(callback.message, callback.from_user.id, offset)


async def render_my_sales(message: Message, telegram_user_id: int,
                          offset: int = 0):
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(telegram_user_id))
        if not user:
            await message.answer("Сначала нажми /start, для регистрации!")
            return
        sales = await list_seller_sales(
            session, user.id, limit=MY_PAGE_SIZE, offset=offset
        )
        total = await count_seller_sales(session, user.id)
        threads = []
        for sale in sales:
            material = sale.material
            if not material:
                continue
            thread = await get_or_create_contact_thread(
                session, material.id, sale.buyer_id, user.id
            )
            buyer_name = (
                sale.buyer.username if sale.buyer and sale.buyer.username
                else "покупатель"
            )
            threads.append((material, buyer_name, thread))

    if not threads or total == 0:
        await message.answer("У тебя пока нет продаж.")
        return
    lines = [f"📈 Получений: {total}", ""]
    for material, buyer_name, thread in threads:
        lines.append(f"📄 {material.title} — {buyer_name}")
    await message.answer("\n".join(lines))
    for material, buyer_name, thread in threads:
        await message.answer(
            f"💬 Чат по «{material.title}» ({buyer_name})",
            reply_markup=chat_keyboard(thread.id, "💬 Написать покупателю"),
        )
    nav = list_nav_keyboard("my_sales", offset, total, MY_PAGE_SIZE)
    if nav:
        await message.answer(
            f"Продажи: {offset + 1}–{offset + len(threads)} из {total}",
            reply_markup=nav,
        )


@router.message(Command("my_sales"))
async def cmd_my_sales(message: Message):
    await render_my_sales(message, message.from_user.id)


@router.callback_query(F.data.startswith("my_sales:"))
async def my_sales_page(callback: CallbackQuery):
    offset = int(callback.data.split(":", 1)[1])
    await callback.answer()
    await render_my_sales(callback.message, callback.from_user.id, offset)


@router.callback_query(F.data.startswith("chat:"))
async def open_chat(callback: CallbackQuery, state: FSMContext):
    thread_id = int(callback.data.split(":", 1)[1])
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(callback.from_user.id))
        thread = await get_contact_thread_for_user(
            session,
            thread_id,
            user.id if user else -1,
        )
        if not user or not thread:
            await callback.answer("Чат недоступен.", show_alert=True)
            return
        messages = await list_contact_messages(session, thread.id)
        await mark_thread_read(session, thread.id, user.id)

    await state.set_state(ChatState.waiting_message)
    await state.update_data(contact_thread_id=thread.id)
    if messages:
        history = "\n".join(
            f"{'Ты' if item.sender_id == user.id else 'Собеседник'}: "
            f"{item.text}"
            for item in messages[-10:]
        )
        await callback.message.answer(f"История чата:\n{history}")
    await callback.message.answer(
        "Напиши сообщение. Для выхода используй /cancel."
    )
    await callback.answer()


@router.message(ChatState.waiting_message, F.text)
async def send_chat_message(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text or len(text) > 2000:
        await message.answer(
            "Сообщение должно содержать от 1 до 2000 символов."
        )
        return

    data = await state.get_data()
    thread_id = data.get("contact_thread_id")
    if not thread_id:
        await state.clear()
        await message.answer("Чат недоступен.")
        return
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(message.from_user.id))
        thread = await get_contact_thread_for_user(
            session, thread_id, user.id if user else -1
        )
        if not user or not thread:
            await state.clear()
            await message.answer("Чат недоступен.")
            return
        await create_chat_message(session, thread.id, user.id, text)
        recipient_id = (
            thread.seller_id if user.id == thread.buyer_id
            else thread.buyer_id
        )
        recipient = await get_user_by_id(session, recipient_id)
        material_title = thread.material.title

    if not recipient or recipient.tg_id.startswith("deleted_"):
        await message.answer("Собеседник удалил аккаунт.")
        return
    await message.bot.send_message(
        chat_id=recipient.tg_id,
        text=(
            f"Новое сообщение по материалу «{material_title}»:\n"
            f"{text}"
        ),
        reply_markup=chat_keyboard(thread.id, "💬 Ответить"),
    )
    await message.answer("Сообщение отправлено.")


@router.callback_query(F.data.startswith("contact:"))
async def contact_author(callback: CallbackQuery, state: FSMContext):
    material_id = int(callback.data.split(":", 1)[1])
    async with async_session_maker() as session:
        buyer = await get_user_by_tg(session, str(callback.from_user.id))
        material = await get_material(session, material_id)
        if not buyer or not material:
            await callback.answer("Материал недоступен.", show_alert=True)
            return
        if material.seller_id == buyer.id:
            await callback.answer("Это твой материал.", show_alert=True)
            return
        thread = await get_or_create_contact_thread(
            session, material.id, buyer.id, material.seller_id
        )
        messages = await list_contact_messages(session, thread.id)
        await mark_thread_read(session, thread.id, buyer.id)
    await state.set_state(ChatState.waiting_message)
    await state.update_data(contact_thread_id=thread.id)
    if messages:
        history = "\n".join(
            f"{'Ты' if item.sender_id == buyer.id else 'Собеседник'}: "
            f"{item.text}"
            for item in messages[-10:]
        )
        await callback.message.answer(f"История чата:\n{history}")
    await callback.message.answer(
        "Напиши автору. Здесь можно обсудить содержание или каталог."
    )
    await callback.answer()

