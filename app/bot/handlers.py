import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
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
from app.bot.states import UploadMaterial

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


@router.message(Command("upload"))
async def start_upload(message: Message, state: FSMContext):
    if not await get_user_for_message(message):
        await message.answer("Сначала нажми /start, для регистрации!")
        return
    await state.set_state(UploadMaterial.waiting_document)
    await message.answer(
        "Пришли документ PDF, DOC, DOCX, JPG, PNG или ZIP размером до 50 МБ."
    )


@router.message(Command("cancel"))
async def cancel_action(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Текущее действие отменено.")


async def get_user_for_message(message: Message):
    async with async_session_maker() as session:
        return await get_user_by_tg(session, str(message.from_user.id))


@router.message(UploadMaterial.waiting_document, F.document)
async def upload_document(message: Message, state: FSMContext):
    allowed_extensions = {"pdf", "doc", "docx", "jpg", "png", "zip"}
    file_name = message.document.file_name or ""
    extension = (
        file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    )
    if extension not in allowed_extensions:
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

    await state.update_data(file_id=message.document.file_id)
    await state.set_state(UploadMaterial.waiting_title)
    await message.answer("Введи название материала:")


@router.message(UploadMaterial.waiting_document)
async def upload_document_invalid(message: Message):
    await message.answer(
        "Нужно отправить документом файл поддерживаемого формата."
    )


@router.message(UploadMaterial.waiting_title, F.text)
async def upload_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if not title or len(title) > 200:
        await message.answer("Название должно содержать от 1 до 200 символов.")
        return
    await state.update_data(title=title)
    await state.set_state(UploadMaterial.waiting_subject)
    await message.answer("Введи название предмета:")


@router.message(UploadMaterial.waiting_subject, F.text)
async def upload_subject(message: Message, state: FSMContext):
    subject = message.text.strip()
    if not subject or len(subject) > 100:
        await message.answer("Предмет должен содержать от 1 до 100 символов.")
        return
    await state.update_data(subject=subject)
    await state.set_state(UploadMaterial.waiting_professor)
    await message.answer("Введи фамилию или имя преподавателя:")


@router.message(UploadMaterial.waiting_professor, F.text)
async def upload_professor(message: Message, state: FSMContext):
    professor = message.text.strip()
    if not professor or len(professor) > 100:
        await message.answer(
            "Имя преподавателя должно быть от 1 до 100 символов."
        )
        return
    await state.update_data(professor=professor)
    await state.set_state(UploadMaterial.waiting_work_type)
    await message.answer("Введи тип работы, например: конспект, лабораторная:")


@router.message(UploadMaterial.waiting_work_type, F.text)
async def upload_work_type(message: Message, state: FSMContext):
    work_type = message.text.strip()
    if not work_type or len(work_type) > 100:
        await message.answer(
            "Тип работы должен содержать от 1 до 100 символов."
        )
        return
    await state.update_data(work_type=work_type)
    await state.set_state(UploadMaterial.waiting_description)
    await message.answer("Добавь описание до 2000 символов или напиши «нет»:")


@router.message(UploadMaterial.waiting_description, F.text)
async def upload_description(message: Message, state: FSMContext):
    description = message.text.strip()
    if description.lower() == "нет":
        description = ""
    if len(description) > 2000:
        await message.answer("Описание не должно быть длиннее 2000 символов.")
        return

    data = await state.update_data(description=description)
    seller = await get_user_for_message(message)
    if not seller:
        await state.clear()
        await message.answer("Сессия регистрации не найдена. Нажми /start.")
        return

    async with async_session_maker() as session:
        material = await create_material(
            session=session,
            seller_id=seller.id,
            title=data["title"],
            price=0,
            file_id=data["file_id"],
            subject=data["subject"],
            professor=data["professor"],
            work_type=data["work_type"],
            description=description,
        )
    await state.clear()
    await message.answer(f"Материал «{material.title}» добавлен в каталог.")


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
