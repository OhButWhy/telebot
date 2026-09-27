from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Каталог"),
            KeyboardButton(text="Поиск"),
        ],
        [
            KeyboardButton(text="Загрузить"),
            KeyboardButton(text="Мои материалы"),
        ],
        [
            KeyboardButton(text="Мои получения"),
            KeyboardButton(text="Профиль"),
        ],
        [KeyboardButton(text="Чаты"), KeyboardButton(text="Удалить аккаунт")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выбери действие",
)


UPLOAD_FILES_MENU = ReplyKeyboardMarkup(
    keyboard=[[
        KeyboardButton(text="Готово"),
        KeyboardButton(text="Отмена"),
    ]],
    resize_keyboard=True,
    input_field_placeholder="Отправь файл или заверши загрузку",
)


EDIT_FILE_MENU = ReplyKeyboardMarkup(
    keyboard=[[
        KeyboardButton(text="Пропустить"),
        KeyboardButton(text="Отмена"),
    ]],
    resize_keyboard=True,
    input_field_placeholder="Добавь файл или пропусти",
)


def material_caption(material, with_author: bool = True) -> str:
    lines = [
        material.title,
        f"Предмет: {material.subject}",
        f"Преподаватель: {material.professor}",
    ]
    if with_author:
        author = material.seller.username if material.seller else None
        lines.append(f"by {author or 'неизвестный автор'}")
    return "\n".join(lines)

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

def chat_keyboard(thread_id: int, label: str = "💬 Открыть чат") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=label,
            callback_data=f"chat:{thread_id}",
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


def list_nav_keyboard(prefix: str, offset: int, total: int,
                      page_size: int) -> InlineKeyboardMarkup | None:
    buttons = []
    if offset > 0:
        buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"{prefix}:{max(0, offset - page_size)}",
        ))
    if offset + page_size < total:
        buttons.append(InlineKeyboardButton(
            text="Дальше ➡️",
            callback_data=f"{prefix}:{offset + page_size}",
        ))
    if not buttons:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Вуз",
            callback_data="profile_edit:university",
        )],
        [InlineKeyboardButton(
            text="Факультет",
            callback_data="profile_edit:faculty",
        )],
        [InlineKeyboardButton(
            text="Курс",
            callback_data="profile_edit:course",
        )],
        [InlineKeyboardButton(
            text="⬅️ В меню",
            callback_data="profile_back",
        )],
    ])


def profile_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="profile_back",
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
