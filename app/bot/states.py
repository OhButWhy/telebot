from aiogram.fsm.state import State, StatesGroup


class UploadMaterial(StatesGroup):
    waiting_document = State()
    waiting_title = State()
    waiting_subject = State()
    waiting_custom_subject = State()
    waiting_professor = State()
    waiting_work_type = State()
    waiting_description = State()


class ProfileSetup(StatesGroup):
    waiting_university = State()
    waiting_faculty = State()
    waiting_course = State()


class ChatState(StatesGroup):
    waiting_message = State()


class SearchState(StatesGroup):
    waiting_query = State()
