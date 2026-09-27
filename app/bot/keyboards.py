from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


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
        [KeyboardButton(text="Чаты"), KeyboardButton(text="Настройки")],
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
