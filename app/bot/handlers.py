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
    create_chat_message,
    delete_user_account,
    get_material,
    get_or_create_transaction,
    get_transaction_for_user,
    get_user_by_id,
    get_user_by_tg,
    list_chat_messages,
    list_user_materials,
    list_user_transactions,
    list_materials,
    update_user_profile,
)
from app.bot.keyboards import MAIN_MENU
from app.bot.states import ChatState, ProfileSetup, SearchState, UploadMaterial

logger = logging.getLogger(__name__)
router = Router()


async def show_main_menu(message: Message):
    await message.answer("Главное меню:", reply_markup=MAIN_MENU)


@router.message(F.text == "Каталог")
async def menu_catalog(message: Message):
    await cmd_catalog(message)


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


@router.message(F.text.in_({"👤 Профиль", "⚙️ Профиль"}))
async def menu_profile(message: Message, state: FSMContext):
    await edit_profile(message, state)


@router.message(F.text == "Чаты")
async def menu_chats(message: Message):
    await cmd_my_purchases(message)


def material_keyboard(material_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Открыть карточку",
            callback_data=f"material:{material_id}",
        ),
    ]])


def material_detail_keyboard(material_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Получить материал",
            callback_data=f"get_material:{material_id}",
        ),
    ]])


def chat_keyboard(transaction_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Написать продавцу",
            callback_data=f"chat:{transaction_id}",
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
                       offset: int = 0):
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(message.from_user.id))
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
        transaction = await get_or_create_transaction(
            session,
            material.id,
            buyer.id,
        )

    await callback.message.bot.send_document(
        chat_id=callback.from_user.id,
        document=material.telegram_file_id,
    )
    await callback.message.answer(
        "Можешь написать продавцу по этому материалу:",
        reply_markup=chat_keyboard(transaction.id),
    )
    await callback.answer("Материал отправлен")


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
        f"Тип: {material.work_type}\n"
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
        transaction = await get_transaction_for_user(
            session,
            data.get("transaction_id", -1),
            user.id if user else -1,
        )
        if not user or not transaction:
            await state.clear()
            await message.answer("Чат недоступен.")
            return
        await create_chat_message(session, transaction.id, user.id, text)
        recipient_id = (
            transaction.material.seller_id
            if user.id == transaction.buyer_id
            else transaction.buyer_id
        )
        recipient = await get_user_by_id(session, recipient_id)

    if not recipient or recipient.tg_id.startswith("deleted_"):
        await message.answer("Собеседник удалил аккаунт.")
        return
    await message.bot.send_message(
        chat_id=recipient.tg_id,
        text=(
            f"Новое сообщение по материалу «{transaction.material.title}»:\n"
            f"{text}"
        ),
    )
    await message.answer("Сообщение отправлено.")
