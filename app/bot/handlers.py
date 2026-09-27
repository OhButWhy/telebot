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
    add_material_file,
    create_user,
    create_topic,
    create_chat_message,
    create_report,
    delete_material,
    delete_user_account,
    get_material,
    get_contact_thread_for_user,
    get_or_create_transaction,
    get_or_create_contact_thread,
    get_transaction_for_user,
    get_user_transaction_for_material,
    count_materials,
    count_topics,
    get_subject,
    get_topic,
    get_user_by_id,
    get_user_by_tg,
    list_chat_messages,
    list_contact_messages,
    list_user_materials,
    list_user_chats,
    list_user_transactions,
    list_materials,
    list_subjects,
    list_topics,
    save_material_rating,
    update_user_profile,
    update_material,
)
from app.bot.keyboards import EDIT_FILE_MENU, MAIN_MENU, UPLOAD_FILES_MENU
from app.bot.states import (
    ChatState,
    EditMaterialState,
    ProfileSetup,
    ReportState,
    SearchState,
    TopicState,
    UploadMaterial,
)

logger = logging.getLogger(__name__)
router = Router()


async def show_main_menu(message: Message):
    await message.answer("Главное меню:", reply_markup=MAIN_MENU)


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


@router.message(F.text == "Настройки")
async def menu_settings(message: Message):
    await cmd_delete_account(message)


def material_keyboard(material_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Открыть карточку",
            callback_data=f"material:{material_id}",
        ),
    ]])


def material_detail_keyboard(material_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Получить материал",
            callback_data=f"get_material:{material_id}",
        )],
        [InlineKeyboardButton(
            text="Написать автору",
            callback_data=f"contact:{material_id}",
        )],
        [InlineKeyboardButton(
            text="Пожаловаться",
            callback_data=f"report:{material_id}",
        )],
    ])


def chat_keyboard(transaction_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Написать продавцу",
            callback_data=f"chat:{transaction_id}",
        ),
    ]])


def rating_keyboard(material_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Спасибо",
            callback_data=f"rating:thanks:{material_id}",
        ),
        InlineKeyboardButton(
            text="Неоч",
            callback_data=f"rating:not_ouch:{material_id}",
        ),
    ]])


def catalog_keyboard(offset: int, has_next: bool,
                     search_term: str | None = None):
    if not has_next and offset == 0:
        return None
    buttons = []
    query_suffix = f":{search_term}" if search_term else ""
    if offset > 0:
        buttons.append(InlineKeyboardButton(
            text="Назад",
            callback_data=f"catalog:{max(0, offset - 10)}{query_suffix}",
        ))
    if has_next:
        buttons.append(InlineKeyboardButton(
            text="Дальше",
            callback_data=f"catalog:{offset + 10}{query_suffix}",
        ))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


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


def delete_material_keyboard(material_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Удалить материал",
            callback_data=f"delete_material:confirm:{material_id}",
        ),
        InlineKeyboardButton(
            text="Отмена",
            callback_data="delete_material:cancel",
        ),
    ]])


def edit_material_keyboard(material_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Редактировать",
            callback_data=f"edit_material:{material_id}",
        ),
        InlineKeyboardButton(
            text="Удалить",
            callback_data=f"delete_material:confirm:{material_id}",
        ),
    ]])


def subject_keyboard(subjects) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text=subject.name,
            callback_data=f"subject:{subject.id}",
        )
        for subject in subjects
    ]
    buttons.append(InlineKeyboardButton(
        text="Другое",
        callback_data="subject:other",
    ))
    return InlineKeyboardMarkup(
        inline_keyboard=[buttons[index:index + 2]
                         for index in range(0, len(buttons), 2)]
    )


def browse_subject_keyboard(subjects) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(
        text=subject.name,
        callback_data=f"browse_subject:{subject.id}",
    ) for subject in subjects]
    return InlineKeyboardMarkup(
        inline_keyboard=[buttons[index:index + 2]
                         for index in range(0, len(buttons), 2)]
    )


def nav_keyboard(subject_id: int, topic_id: int,
                 parent_topic_id: int | None = None) -> InlineKeyboardMarkup:
    rows = []
    if topic_id:
        target = parent_topic_id or 0
        rows.append([InlineKeyboardButton(
            text="Назад в раздел",
            callback_data=f"browse_topic:{subject_id}:{target}:0",
        )])
    rows.append([InlineKeyboardButton(
        text="К предметам",
        callback_data="browse_subjects",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pagination_keyboard(prefix: str, subject_id: int, topic_id: int,
                        topics_offset: int, materials_offset: int,
                        offset: int, total: int) -> InlineKeyboardMarkup | None:
    buttons = []
    if offset > 0:
        buttons.append(InlineKeyboardButton(
            text="Назад",
            callback_data=(
                f"{prefix}:{subject_id}:{topic_id}:"
                f"{topics_offset}:{materials_offset}:{max(0, offset - 10)}"
            ),
        ))
    if offset + 10 < total:
        buttons.append(InlineKeyboardButton(
            text="Дальше",
            callback_data=(
                f"{prefix}:{subject_id}:{topic_id}:"
                f"{topics_offset}:{materials_offset}:{offset + 10}"
            ),
        ))
    return InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None


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
        subject.name if topic_id == 0
        else f"{subject.name} → {current_topic.name if current_topic else 'Топик'}"
    )
    await message.answer(header)

    if topics:
        await message.answer("Топики:")
        for topic in topics[:10]:
            await message.answer(
                f"Топик: {topic.name}\nМатериалов: {topic.material_count}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Открыть топик",
                        callback_data=f"browse_topic:{subject_id}:{topic.id}:0",
                    ),
                ]]),
            )
        topic_pages = pagination_keyboard(
            "browse_topics", subject_id, topic_id,
            topics_offset, materials_offset, topics_offset, topic_total,
        )
        if topic_pages:
            await message.answer("Страницы топиков:",
                                 reply_markup=topic_pages)
    elif topic_id == 0:
        await message.answer("В этом предмете пока нет топиков.")

    if not materials:
        await message.answer("Материалов в этом разделе пока нет.")
    else:
        for material in materials[:10]:
            await message.answer(
                f"{material.title}\n"
                f"Предмет: {material.subject}\n"
                f"Преподаватель: {material.professor}",
                reply_markup=material_keyboard(material.id),
            )
        material_pages = pagination_keyboard(
            "browse_materials", subject_id, topic_id,
            topics_offset, materials_offset, materials_offset,
            material_total,
        )
        if material_pages:
            await message.answer("Страницы материалов:",
                                 reply_markup=material_pages)

    await message.answer(
        "Действия:",
        reply_markup=nav_keyboard(
            subject_id,
            topic_id,
            current_topic.parent_topic_id if current_topic else None,
        ),
    )


@router.callback_query(F.data == "browse_subjects")
async def browse_subjects_callback(callback: CallbackQuery):
    await callback.answer()
    await show_subjects(callback.message, callback.from_user.id)


@router.callback_query(F.data.startswith("browse_subject:"))
async def browse_subject_callback(callback: CallbackQuery):
    subject_id = int(callback.data.split(":", 1)[1])
    await callback.answer()
    await show_catalog_page(callback.message, subject_id, 0,
                            callback.from_user.id)


@router.callback_query(F.data.startswith("browse_topic:"))
async def browse_topic_callback(callback: CallbackQuery):
    parts = callback.data.split(":")
    offset = int(parts[3]) if len(parts) > 3 else 0
    await callback.answer()
    await show_catalog_page(
        callback.message,
        int(parts[1]),
        int(parts[2]),
        callback.from_user.id,
        materials_offset=offset,
    )


@router.callback_query(F.data.startswith("browse_topics:"))
async def browse_topics_page_callback(callback: CallbackQuery):
    _, subject_id, topic_id, _, materials_offset, topics_offset = (
        callback.data.split(":")
    )
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
async def browse_materials_page_callback(callback: CallbackQuery):
    _, subject_id, topic_id, topics_offset, _, materials_offset = (
        callback.data.split(":")
    )
    await callback.answer()
    await show_catalog_page(
        callback.message,
        int(subject_id),
        int(topic_id),
        callback.from_user.id,
        topics_offset=int(topics_offset),
        materials_offset=int(materials_offset),
    )


def topic_keyboard(topics, subject_id: int) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text=topic.name,
            callback_data=f"topic:{topic.id}",
        )
        for topic in topics
    ]
    buttons.extend([
        InlineKeyboardButton(
            text="Без топика",
            callback_data=f"topic:none:{subject_id}",
        ),
        InlineKeyboardButton(
            text="Добавить топик",
            callback_data=f"topic:new:{subject_id}",
        ),
    ])
    return InlineKeyboardMarkup(
        inline_keyboard=[buttons[index:index + 2]
                         for index in range(0, len(buttons), 2)]
    )


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
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
            await start_profile_setup(message, state)
        else:
            logger.info("Existing user %s", message.from_user.id)
            if (
                user.university == "Unknown"
                or not user.faculty
                or user.course is None
            ):
                await message.answer("Давай заполним профиль.")
                await start_profile_setup(message, state)
            else:
                await message.answer("Привет! Ты уже в системе.")
                await show_main_menu(message)


async def start_profile_setup(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(ProfileSetup.waiting_university)
    await message.answer("Напиши название своего вуза:")


@router.message(Command("profile"))
async def edit_profile(message: Message, state: FSMContext):
    if not await get_user_for_message(message):
        await message.answer("Сначала нажми /start, для регистрации!")
        return
    await start_profile_setup(message, state)


@router.message(ProfileSetup.waiting_university, F.text)
async def profile_university(message: Message, state: FSMContext):
    university = message.text.strip()
    if not university or len(university) > 200:
        await message.answer("Название вуза должно быть от 1 до 200 символов.")
        return
    await state.update_data(university=university)
    await state.set_state(ProfileSetup.waiting_faculty)
    await message.answer("Напиши свой факультет:")


@router.message(ProfileSetup.waiting_faculty, F.text)
async def profile_faculty(message: Message, state: FSMContext):
    faculty = message.text.strip()
    if not faculty or len(faculty) > 200:
        await message.answer(
            "Название факультета должно быть от 1 до 200 символов."
        )
        return
    await state.update_data(faculty=faculty)
    await state.set_state(ProfileSetup.waiting_course)
    await message.answer("Напиши номер курса от 1 до 6:")


@router.message(ProfileSetup.waiting_course, F.text)
async def profile_course(message: Message, state: FSMContext):
    try:
        course = int(message.text.strip())
    except ValueError:
        await message.answer("Курс должен быть целым числом от 1 до 6.")
        return
    if course < 1 or course > 6:
        await message.answer("Курс должен быть целым числом от 1 до 6.")
        return

    data = await state.get_data()
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(message.from_user.id))
        if not user:
            await state.clear()
            await message.answer("Профиль не найден. Нажми /start заново.")
            return
        await update_user_profile(
            session=session,
            user=user,
            university=data["university"],
            faculty=data["faculty"],
            course=course,
        )
    await state.clear()
    await message.answer(
        "Профиль сохранён. Теперь доступен каталог материалов."
    )
    await show_main_menu(message)


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
async def cancel_action(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Текущее действие отменено.")


@router.message(F.text == "Отмена")
async def cancel_button(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Текущее действие отменено.", reply_markup=MAIN_MENU)


@router.message(Command("skip"))
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


@router.message(EditMaterialState.waiting_file, F.text == "Пропустить")
async def skip_edit_file_button(message: Message, state: FSMContext):
    await skip_edit_file(message, state)


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
async def finish_document_upload(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("subject_id"):
        await state.set_state(UploadMaterial.waiting_title)
        await message.answer("Введи название материала:")
        return
    await prompt_subject_selection(message, state)


@router.message(UploadMaterial.waiting_documents, Command("done"))
async def finish_document_upload_command(message: Message, state: FSMContext):
    await finish_document_upload(message, state)


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
            work_type="Материал",
            description=description,
        )
        for file_id in data["file_ids"][1:]:
            await add_material_file(session, material.id, file_id)
    await state.clear()
    await message.answer(f"Материал «{material.title}» добавлен в каталог.")
    await show_main_menu(message)


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
            limit=11,
            offset=offset,
        )

    if not materials:
        text = "Поиск ничего не нашёл." if search_term else (
            "В каталоге пока нет материалов для твоего вуза."
        )
        await message.answer(text)
        return

    has_next = len(materials) > 10
    for material in materials[:10]:
        await message.answer(
            f"{material.title}\n"
            f"Предмет: {material.subject}\n"
            f"Преподаватель: {material.professor}\n"
            f"Цена: {material.price:.0f} ₽",
            reply_markup=material_keyboard(material.id),
        )
    await message.answer(
        f"Страница {offset // 10 + 1}",
        reply_markup=catalog_keyboard(offset, has_next, search_term),
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
    await callback.message.edit_text("Материал скрыт из каталога.")


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
        transaction = await get_or_create_transaction(
            session,
            material.id,
            buyer.id,
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
        reply_markup=chat_keyboard(transaction.id),
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


@router.callback_query(F.data.startswith("contact:"))
async def contact_author(callback: CallbackQuery, state: FSMContext):
    material_id = int(callback.data.split(":", 1)[1])
    async with async_session_maker() as session:
        buyer = await get_user_by_tg(session, str(callback.from_user.id))
        material = await get_material(session, material_id)
        if not buyer or not material or material.status != "active":
            await callback.answer("Материал недоступен.", show_alert=True)
            return
        if material.seller_id == buyer.id:
            await callback.answer("Это твой материал.", show_alert=True)
            return
        thread = await get_or_create_contact_thread(
            session, material.id, buyer.id, material.seller_id
        )
        messages = await list_contact_messages(session, thread.id)
    await state.set_state(ChatState.waiting_message)
    await state.update_data(contact_thread_id=thread.id, transaction_id=None)
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


@router.callback_query(F.data.startswith("material:"))
async def material_detail_callback(callback: CallbackQuery):
    material_id = int(callback.data.split(":", 1)[1])
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(callback.from_user.id))
        material = await get_material(session, material_id)
        if not user or not material or material.status != "active":
            await callback.answer("Материал недоступен.", show_alert=True)
            return
        if material.seller.university != user.university:
            await callback.answer("Материал недоступен для твоего вуза.",
                                  show_alert=True)
            return

    description = material.description or "Описание отсутствует."
    await callback.message.answer(
        f"{material.title}\n"
        f"Предмет: {material.subject}\n"
        f"Преподаватель: {material.professor}\n"
        f"Описание: {description}",
        reply_markup=material_detail_keyboard(material.id),
    )
    await callback.answer()


@router.message(Command("my_materials"))
async def cmd_my_materials(message: Message):
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(message.from_user.id))
        if not user:
            await message.answer("Сначала нажми /start, для регистрации!")
            return
        materials = await list_user_materials(session, user.id)

    if not materials:
        await message.answer("Ты ещё не загрузил материалы.")
        return
    for material in materials:
        await message.answer(
            f"{material.title}\n"
            f"Предмет: {material.subject}\n"
            f"Статус: {material.status}",
            reply_markup=(
                edit_material_keyboard(material.id)
                if material.status == "active" else None
            ),
        )


@router.message(Command("my_purchases"))
async def cmd_my_purchases(message: Message):
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(message.from_user.id))
        if not user:
            await message.answer("Сначала нажми /start, для регистрации!")
            return
        transactions = await list_user_transactions(session, user.id)

    if not transactions:
        await message.answer("Ты ещё не получал материалы.")
        return
    for transaction in transactions:
        await message.answer(
            f"Получен материал: {transaction.material.title}\n"
            f"Статус: {transaction.status}\n"
            f"Транзакция: {transaction.id}",
            reply_markup=chat_keyboard(transaction.id),
        )


@router.message(Command("my_chats"))
async def cmd_my_chats(message: Message):
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(message.from_user.id))
        if not user:
            await message.answer("Сначала нажми /start, для регистрации!")
            return
        transactions = await list_user_chats(session, user.id)

    if not transactions:
        await message.answer("У тебя пока нет чатов.")
        return
    for transaction in transactions:
        await message.answer(
            f"Чат по материалу: {transaction.material.title}\n"
            f"Транзакция: {transaction.id}",
            reply_markup=chat_keyboard(transaction.id),
        )


@router.callback_query(F.data.startswith("chat:"))
async def open_chat(callback: CallbackQuery, state: FSMContext):
    transaction_id = int(callback.data.split(":", 1)[1])
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(callback.from_user.id))
        transaction = await get_transaction_for_user(
            session,
            transaction_id,
            user.id if user else -1,
        )
        if not user or not transaction:
            await callback.answer("Чат недоступен.", show_alert=True)
            return
        messages = await list_chat_messages(session, transaction.id)

    await state.set_state(ChatState.waiting_message)
    await state.update_data(transaction_id=transaction.id)
    if messages:
        history = "\n".join(
            f"{'Ты' if item.sender_id == user.id else 'Собеседник'}: "
            f"{item.text}"
            for item in messages[-10:]
        )
        await callback.message.answer(f"История чата:\n{history}")
    await callback.message.answer(
        "Напиши сообщение продавцу. Для выхода используй /cancel."
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
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(message.from_user.id))
        if not user:
            await state.clear()
            await message.answer("Чат недоступен.")
            return
        contact_thread_id = data.get("contact_thread_id")
        transaction = None
        if contact_thread_id:
            thread = await get_contact_thread_for_user(
                session, contact_thread_id, user.id
            )
            if not thread:
                await state.clear()
                await message.answer("Чат недоступен.")
                return
            await create_chat_message(
                session,
                transaction_id=None,
                sender_id=user.id,
                text=text,
                contact_thread_id=thread.id,
            )
            recipient_id = (
                thread.seller_id
                if user.id == thread.buyer_id
                else thread.buyer_id
            )
            material_title = thread.material.title
        else:
            transaction = await get_transaction_for_user(
                session,
                data.get("transaction_id", -1),
                user.id,
            )
            if not transaction:
                await state.clear()
                await message.answer("Чат недоступен.")
                return
            await create_chat_message(session, transaction.id, user.id, text)
            recipient_id = (
                transaction.material.seller_id
                if user.id == transaction.buyer_id
                else transaction.buyer_id
            )
            material_title = transaction.material.title
        recipient = await get_user_by_id(session, recipient_id)

    if not recipient or recipient.tg_id.startswith("deleted_"):
        await message.answer("Собеседник удалил аккаунт.")
        return
    await message.bot.send_message(
        chat_id=recipient.tg_id,
        text=(
            f"Новое сообщение по материалу «{material_title}»:\n"
            f"{text}"
        ),
    )
    await message.answer("Сообщение отправлено.")
