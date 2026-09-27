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

from app.bot.common import get_user_for_message, show_main_menu
from app.bot.keyboards import (
    MAIN_MENU,
    UPLOAD_FILES_MENU,
    subject_keyboard,
    topic_keyboard,
)
from app.bot.states import TopicState, UploadMaterial
from app.db.queries import (
    add_material_file,
    create_material,
    create_topic,
    get_subject,
    list_subjects,
    list_topics,
)
from app.db.session import async_session_maker

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("upload"))
async def start_upload(message: Message, state: FSMContext,
                       subject_id: int | None = None,
                       topic_id: int | None = None):
    if not await get_user_for_message(message):
        await message.answer("Сначала нажми /start, для регистрации!")
        return
    await state.clear()
    await state.update_data(subject_id=subject_id, topic_id=topic_id)
    await state.set_state(UploadMaterial.waiting_document)
    await message.answer(
        "Пришли документ PDF, DOC, DOCX, JPG, PNG или ZIP размером до 50 МБ."
    )


@router.message(Command("cancel"))
@router.message(F.text == "Отмена")
async def cancel_action(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Текущее действие отменено.", reply_markup=MAIN_MENU)


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

    await state.update_data(file_ids=[message.document.file_id])
    data = await state.get_data()
    if data.get("subject_id"):
        async with async_session_maker() as session:
            subject = await get_subject(session, data["subject_id"])
        if subject:
            await state.update_data(subject=subject.name)
            await state.set_state(UploadMaterial.waiting_documents)
            await message.answer(
                "Файл принят. Можешь отправить ещё файлы или нажми «Готово».",
                reply_markup=UPLOAD_FILES_MENU,
            )
            return
    await state.set_state(UploadMaterial.waiting_documents)
    await message.answer(
        "Файл принят. Можешь отправить ещё файлы или нажми «Готово».",
        reply_markup=UPLOAD_FILES_MENU,
    )


@router.message(UploadMaterial.waiting_documents, F.document)
async def upload_additional_document(message: Message, state: FSMContext):
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
    data = await state.get_data()
    file_ids = data.get("file_ids", [])
    file_ids.append(message.document.file_id)
    await state.update_data(file_ids=file_ids)
    await message.answer(
        f"Файл принят. Всего файлов: {len(file_ids)}. "
        "Отправь ещё или нажми «Готово».",
        reply_markup=UPLOAD_FILES_MENU,
    )


async def prompt_subject_selection(message: Message, state: FSMContext):
    async with async_session_maker() as session:
        subjects = await list_subjects(session)
    await state.set_state(UploadMaterial.waiting_subject)
    await message.answer(
        "Выбери предмет или направление:",
        reply_markup=subject_keyboard(subjects),
    )


@router.message(UploadMaterial.waiting_documents, F.text == "Готово")
@router.message(UploadMaterial.waiting_documents, Command("done"))
async def finish_document_upload(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("subject_id"):
        await state.set_state(UploadMaterial.waiting_title)
        await message.answer("Введи название материала:")
        return
    await prompt_subject_selection(message, state)


@router.message(UploadMaterial.waiting_document)
async def upload_document_invalid(message: Message):
    await message.answer(
        "Нужно отправить документом файл поддерживаемого формата."
    )


@router.callback_query(
    UploadMaterial.waiting_subject,
    F.data.startswith("subject:"),
)
async def upload_subject_callback(callback: CallbackQuery, state: FSMContext):
    value = callback.data.split(":", 1)[1]
    if value == "other":
        await state.set_state(UploadMaterial.waiting_custom_subject)
        await callback.message.answer("Напиши название предмета:")
        await callback.answer()
        return

    async with async_session_maker() as session:
        subject = await get_subject(session, int(value))
        topics = await list_topics(session, int(value))
    if not subject:
        await callback.answer("Предмет недоступен.", show_alert=True)
        return
    await state.update_data(subject_id=subject.id, subject=subject.name)
    await state.set_state(UploadMaterial.waiting_topic)
    await callback.message.answer(
        "Выбери топик или создай новый:",
        reply_markup=topic_keyboard(topics, subject.id),
    )
    await callback.answer()


@router.callback_query(
    UploadMaterial.waiting_topic,
    F.data.startswith("topic:"),
)
async def upload_topic_callback(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    if parts[1] == "new":
        await state.update_data(topic_subject_id=int(parts[2]))
        await state.set_state(TopicState.waiting_name)
        await callback.message.answer("Введи название нового топика:")
        await callback.answer()
        return
    topic_id = None if parts[1] == "none" else int(parts[1])
    await state.update_data(topic_id=topic_id)
    await state.set_state(UploadMaterial.waiting_title)
    await callback.message.answer("Введи название материала:")
    await callback.answer()


@router.message(TopicState.waiting_name, F.text)
async def create_topic_for_upload(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name or len(name) > 100:
        await message.answer(
            "Название топика должно быть от 1 до 100 символов."
        )
        return
    data = await state.get_data()
    creator = await get_user_for_message(message)
    async with async_session_maker() as session:
        topic = await create_topic(
            session,
            subject_id=data["topic_subject_id"],
            creator_id=creator.id,
            name=name,
        )
    await state.update_data(topic_id=topic.id)
    await state.set_state(UploadMaterial.waiting_title)
    await message.answer("Топик создан. Введи название материала:")


@router.message(UploadMaterial.waiting_subject, F.text)
async def upload_subject_button_required(message: Message):
    await message.answer("Выбери предмет кнопкой выше или нажми «Другое».")


@router.message(UploadMaterial.waiting_custom_subject, F.text)
async def upload_custom_subject(message: Message, state: FSMContext):
    subject = message.text.strip()
    if not subject or len(subject) > 100:
        await message.answer("Предмет должен содержать от 1 до 100 символов.")
        return
    await state.update_data(subject=subject, subject_id=None)
    await state.set_state(UploadMaterial.waiting_title)
    await message.answer("Введи название материала:")


@router.message(UploadMaterial.waiting_title, F.text)
async def upload_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if not title or len(title) > 200:
        await message.answer("Название должно содержать от 1 до 200 символов.")
        return
    await state.update_data(title=title)
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
            file_id=data["file_ids"][0],
            subject_id=data.get("subject_id"),
            topic_id=data.get("topic_id"),
            subject=data["subject"],
            professor=data["professor"],
            description=description,
        )
        for file_id in data["file_ids"][1:]:
            await add_material_file(session, material.id, file_id)
    await state.clear()
    await message.answer(f"Материал «{material.title}» добавлен в каталог.")
    await show_main_menu(message)

