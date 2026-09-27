from aiogram.fsm.state import State, StatesGroup


class UploadMaterial(StatesGroup):
    waiting_document = State()
    waiting_documents = State()
    waiting_title = State()
    waiting_subject = State()
    waiting_topic = State()
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


class TopicState(StatesGroup):
    waiting_name = State()


class ReportState(StatesGroup):
    waiting_comment = State()


class EditMaterialState(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_order = State()
    waiting_file = State()
