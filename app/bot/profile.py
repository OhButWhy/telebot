import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.common import get_user_for_message, show_main_menu
from app.bot.states import ProfileSetup
from app.db.queries import create_user, get_user_by_tg, update_user_profile
from app.db.session import async_session_maker

logger = logging.getLogger(__name__)
router = Router()


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

