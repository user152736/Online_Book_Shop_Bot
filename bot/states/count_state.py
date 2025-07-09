from aiogram.fsm.state import StatesGroup, State


class CountState(StatesGroup):
    count = State()
