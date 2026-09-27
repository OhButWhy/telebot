import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.common import show_main_menu
from app.bot.keyboards import profile_back_keyboard, profile_keyboard
from app.bot.states import EditProfile, ProfileSetup
from app.db.queries import create_user, get_user_by_tg, update_user_profile
from app.db.session import async_session_maker

logger = logging.getLogger(__name__)
router = Router()

# field -> (label for prompts, max length, allowed numeric range)
FIELDS = {
    "university": ("вуза", 200, None),
    "faculty": ("факультета", 200, None),
    "course": ("курса", None, (1, 6)),
}


def profile_text(user) -> str:
    return (
        "👤 Твой профиль\n\n"
        f"Вуз: {user.university}\n"
        f"Факультет: {user.faculty or '—'}\n"
        f"Курс: {user.course or '—'}"
    )


def field_prompt(field: str) -> str:
    if field == "course":
        return "Введи новый курс от 1 до 6:"
    return f"Введи новое название {FIELDS[field][0]}:"


def validate_field(field: str, raw: str):
    """Returns (value, error)."""
    label, max_length, bounds = FIELDS[field]
    value = raw.strip()
    if bounds:
        try:
            number = int(value)
        except ValueError:
            return None, "Курс должен быть целым числом от 1 до 6."
        if not bounds[0] <= number <= bounds[1]:
            return None, "Курс должен быть целым числом от 1 до 6."
        return number, None
    if not value or len(value) > max_length:
        return None, f"Название {label} должно быть от 1 до {max_length} символов."
    return value, None


def is_profile_filled(user) -> bool:
    return (
        user.university != "Unknown"
        and bool(user.faculty)
        and user.course is not None
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
            if not is_profile_filled(user):
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
@router.message(F.text.in_({"Профиль", "👤 Профиль", "⚙️ Профиль"}))
async def edit_profile(message: Message, state: FSMContext):
    await state.clear()
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(message.from_user.id))
    if not user:
        await message.answer("Сначала нажми /start, для регистрации!")
        return
    if not is_profile_filled(user):
        await message.answer("Давай заполним профиль.")
        await start_profile_setup(message, state)
        return
    await message.answer(profile_text(user), reply_markup=profile_keyboard())


@router.callback_query(F.data.startswith("profile_edit:"))
async def profile_edit_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":", 1)[1]
    if field not in FIELDS:
        await callback.answer("Поле недоступно.", show_alert=True)
        return
    await state.set_state(EditProfile.waiting_value)
    await state.update_data(profile_field=field)
    await callback.answer()
    await callback.message.edit_text(
        field_prompt(field),
        reply_markup=profile_back_keyboard(),
    )


@router.callback_query(F.data == "profile_back")
async def profile_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(callback.from_user.id))
    await callback.answer()
    if not user:
        await callback.message.answer("Профиль не найден. Нажми /start.")
        return
    await callback.message.edit_text(
        profile_text(user),
        reply_markup=profile_keyboard(),
    )


@router.message(EditProfile.waiting_value, F.text)
async def profile_edit_value(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data.get("profile_field")
    if field not in FIELDS:
        await state.clear()
        await message.answer("Что-то пошло не так. Открой профиль заново.")
        return
    value, error = validate_field(field, message.text)
    if error:
        await message.answer(error)
        return

    async with async_session_maker() as session:
        user = await get_user_by_tg(session, str(message.from_user.id))
        if not user:
            await state.clear()
            await message.answer("Профиль не найден. Нажми /start заново.")
            return
        values = {
            "university": user.university,
            "faculty": user.faculty or "",
            "course": user.course,
        }
        values[field] = value
        await update_user_profile(
            session=session,
            user=user,
            university=values["university"],
            faculty=values["faculty"],
            course=values["course"],
        )
    await state.clear()
    await message.answer(profile_text(user), reply_markup=profile_keyboard())


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
