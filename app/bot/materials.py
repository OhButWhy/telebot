import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.common import get_user_for_message
from app.bot.keyboards import (
    chat_keyboard,
    material_caption,
    material_detail_keyboard,
    rating_keyboard,
)
from app.bot.states import ReportState
from app.db.queries import (
    create_report,
    get_material,
    get_or_create_contact_thread,
    get_or_create_transaction,
    get_user_by_tg,
    get_user_transaction_for_material,
    save_material_rating,
)
from app.db.session import async_session_maker

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("get_material:"))
async def get_material_callback(callback: CallbackQuery):
    material_id = int(callback.data.split(":", 1)[1])
    async with async_session_maker() as session:
        buyer = await get_user_by_tg(session, str(callback.from_user.id))
        material = await get_material(session, material_id)
        if not buyer or not material:
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
        thread = await get_or_create_contact_thread(
            session, material.id, buyer.id, material.seller_id
        )

    await callback.message.bot.send_document(
        chat_id=callback.from_user.id,
        document=material.telegram_file_id,
    )
    for material_file in material.files[1:]:
        await callback.message.bot.send_document(
            chat_id=callback.from_user.id,
            document=material_file.telegram_file_id,
        )
    await callback.message.answer(
        "Можешь написать продавцу по этому материалу:",
        reply_markup=chat_keyboard(thread.id, "Написать продавцу"),
    )
    await callback.message.answer(
        "Оцени материал:",
        reply_markup=rating_keyboard(material.id),
    )
    await callback.answer("Материал отправлен")


@router.callback_query(F.data.startswith("rating:"))
async def rate_material(callback: CallbackQuery):
    _, value, material_id_text = callback.data.split(":")
    material_id = int(material_id_text)
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(callback.from_user.id))
        transaction = await get_user_transaction_for_material(
            session,
            material_id,
            user.id if user else -1,
        )
        if not transaction:
            await callback.answer(
                "Оценить можно только полученный материал.",
                show_alert=True,
            )
            return
        await save_material_rating(session, material_id, user.id, value)
    await callback.answer("Оценка сохранена")


@router.callback_query(F.data.startswith("report:"))
async def start_report(callback: CallbackQuery, state: FSMContext):
    material_id = int(callback.data.split(":", 1)[1])
    await state.set_state(ReportState.waiting_comment)
    await state.update_data(report_material_id=material_id)
    await callback.message.answer(
        "Опиши причину жалобы одним сообщением. Для отмены нажми /cancel."
    )
    await callback.answer()


@router.message(ReportState.waiting_comment, F.text)
async def submit_report(message: Message, state: FSMContext):
    comment = message.text.strip()
    if not comment or len(comment) > 2000:
        await message.answer("Комментарий должен быть от 1 до 2000 символов.")
        return
    data = await state.get_data()
    async with async_session_maker() as session:
        reporter = await get_user_for_message(message)
        if not reporter:
            await state.clear()
            await message.answer("Сначала нажми /start.")
            return
        report = await create_report(
            session,
            data["report_material_id"],
            reporter.id,
            comment,
        )
    await state.clear()
    await message.answer(
        f"Жалоба №{report.id} принята. Пока она сохранена для модерации."
    )


@router.callback_query(F.data.startswith("material:"))
async def material_detail_callback(callback: CallbackQuery):
    material_id = int(callback.data.split(":", 1)[1])
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(callback.from_user.id))
        material = await get_material(session, material_id)
        if not user or not material:
            await callback.answer("Материал недоступен.", show_alert=True)
            return
        if material.seller.university != user.university:
            await callback.answer("Материал недоступен для твоего вуза.",
                                  show_alert=True)
            return

    description = material.description or "Описание отсутствует."
    await callback.message.answer(
        f"{material_caption(material)}\n"
        f"Описание: {description}",
        reply_markup=material_detail_keyboard(material.id),
    )
    await callback.answer()

