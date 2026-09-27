import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import EDIT_FILE_MENU
from app.bot.states import EditMaterialState
from app.db.queries import (
    add_material_file,
    get_material,
    get_user_by_tg,
    update_material,
)
from app.db.session import async_session_maker

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("edit_material:"))
async def start_edit_material(callback: CallbackQuery, state: FSMContext):
    material_id = int(callback.data.split(":", 1)[1])
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(callback.from_user.id))
        material = await get_material(session, material_id)
        if not user or not material or material.seller_id != user.id:
            await callback.answer("Можно редактировать только свой материал.",
                                  show_alert=True)
            return
    await state.set_state(EditMaterialState.waiting_title)
    await state.update_data(edit_material_id=material_id)
    await callback.message.answer(
        f"Текущее название: {material.title}\nВведи новое название:"
    )
    await callback.answer()


@router.message(Command("skip"))
@router.message(EditMaterialState.waiting_file, F.text == "Пропустить")
async def skip_edit_file(message: Message, state: FSMContext):
    if await state.get_state() != EditMaterialState.waiting_file.state:
        await message.answer("Сейчас нечего пропускать.")
        return
    data = await state.get_data()
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(message.from_user.id))
        updated = bool(user) and await update_material(
            session,
            data["edit_material_id"],
            user.id,
            title=data["title"],
            description=data["description"],
            sort_order=data["sort_order"],
        )
    await state.clear()
    await message.answer(
        "Материал сохранён без замены файла."
        if updated else "Материал не найден."
    )


@router.message(EditMaterialState.waiting_title, F.text)
async def edit_material_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if not title or len(title) > 200:
        await message.answer("Название должно содержать от 1 до 200 символов.")
        return
    await state.update_data(title=title)
    await state.set_state(EditMaterialState.waiting_description)
    await message.answer("Введи новое описание до 2000 символов:")


@router.message(EditMaterialState.waiting_description, F.text)
async def edit_material_description(message: Message, state: FSMContext):
    description = message.text.strip()
    if len(description) > 2000:
        await message.answer("Описание не должно быть длиннее 2000 символов.")
        return
    await state.update_data(description=description)
    await state.set_state(EditMaterialState.waiting_order)
    await message.answer(
        "Введи позицию в каталоге: целое число от 0 до 100000."
    )


@router.message(EditMaterialState.waiting_order, F.text)
async def edit_material_order(message: Message, state: FSMContext):
    try:
        sort_order = int(message.text.strip())
    except ValueError:
        await message.answer(
            "Позиция должна быть целым числом от 0 до 100000."
        )
        return
    if sort_order < 0 or sort_order > 100000:
        await message.answer(
            "Позиция должна быть целым числом от 0 до 100000."
        )
        return
    await state.update_data(sort_order=sort_order)
    await state.set_state(EditMaterialState.waiting_file)
    await message.answer(
        "Пришли дополнительный файл или нажми «Пропустить».",
        reply_markup=EDIT_FILE_MENU,
    )


@router.message(EditMaterialState.waiting_file, F.document)
async def edit_material_file(message: Message, state: FSMContext):
    file_name = message.document.file_name or ""
    extension = (
        file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    )
    if extension not in {"pdf", "doc", "docx", "jpg", "png", "zip"}:
        await message.answer("Этот формат файла не поддерживается.")
        return
    if (
        message.document.file_size
        and message.document.file_size > 50 * 1024 * 1024
    ):
        await message.answer(
            "Файл слишком большой. Максимальный размер: 50 МБ."
        )
        return
    data = await state.get_data()
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(message.from_user.id))
        updated = bool(user) and await update_material(
            session,
            data["edit_material_id"],
            user.id,
            title=data["title"],
            description=data["description"],
            sort_order=data["sort_order"],
        )
        if updated:
            await add_material_file(
                session,
                data["edit_material_id"],
                message.document.file_id,
                file_name,
            )
    await state.clear()
    await message.answer(
        "Материал обновлён." if updated else "Материал не найден."
    )

