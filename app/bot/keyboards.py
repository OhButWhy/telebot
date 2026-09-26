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
        [KeyboardButton(text="Чаты")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выбери действие",
)
