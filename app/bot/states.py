from aiogram.fsm.state import State, StatesGroup


class UploadMaterial(StatesGroup):
    waiting_document = State()
    waiting_title = State()
    waiting_subject = State()
    waiting_professor = State()
    waiting_work_type = State()
    waiting_description = State()
