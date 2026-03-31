from aiogram.fsm.state import StatesGroup, State

user_temp_passwords = {}

class AuthStates(StatesGroup):
    """States for authentication and output"""
    waiting_for_login = State()
    waiting_for_password = State()
    waiting_for_photos = State()

class Form(StatesGroup):
    """Token (state: FSMContext)"""
    waiting_for_token = State()

class Info:
    """Variables for throwing"""
    form = None
    city = None
    street = None
    home = None
    apartment = None
    count = 0

class Simular(StatesGroup):
    view_first_folder = State()
    view_second_folder = State()

class Operation(StatesGroup):
    send_photo = State()
    view_photo = State()
