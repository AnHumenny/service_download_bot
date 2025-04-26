import asyncio
import datetime
import logging
from functools import wraps
import jwt
from aiogram import Bot, Dispatcher, types
import os
import base64
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command, CommandObject, StateFilter
import subprocess
import lists
from repository import Repo
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv('API_TOKEN')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class SelectInfo(StatesGroup):
    """registered user"""
    register_user = State()

class AuthStates(StatesGroup):
    """states for authentication and output"""
    waiting_for_login = State()
    waiting_for_password = State()

class Form(StatesGroup):
    """token (state: FSMContext)"""
    waiting_for_token = State()

class Info:
    """Variables for throwing"""
    form = None
    city = None
    street = None
    home = None
    apartment = None
    count = 0


async def create_jwt_token(data):
    """create token"""
    token = jwt.encode({
        **data,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }, os.getenv("SECRET_KEY"), algorithm='HS256')
    return token


async def decode_jwt_token(token):
    """decode token"""
    try:
        decoded_data = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=['HS256'])
        return decoded_data
    except jwt.ExpiredSignatureError:
        print("Token has expired.")
        return None
    except jwt.InvalidTokenError:
        print("Invalid token.")
        return None


def token_required(func):
    """check token"""
    @wraps(func)
    async def wrapper(message: types.Message, state: FSMContext, *args, **kwargs):
        data = await state.get_data()
        token = data.get("jwt_token")
        if not token:
            await message.answer("Нет сохранённого токена. Пройдите авторизацию через /start.")
            return None
        decoded_data = await decode_jwt_token(token)
        if decoded_data:
            return await func(message, state=state, *args, **kwargs)
        else:
            await message.answer("Токен недействителен или истёк. Авторизуйтесь снова.")
            return None
    return wrapper

@dp.message(StateFilter(None), Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    """start(enter login)"""
    await message.answer("Введите логин:")
    await state.set_state(AuthStates.waiting_for_login)

@dp.message(AuthStates.waiting_for_login)
async def process_login(message: types.Message, state: FSMContext):
    """start(enter password)"""
    await state.update_data(login=message.text)
    await message.answer("Теперь введите пароль:")
    await state.set_state(AuthStates.waiting_for_password)


@dp.message(AuthStates.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    login = user_data.get('login')
    password = message.text
    encoded_password = base64.b64encode(password.encode('utf-8'))
    result = await Repo.select_pass(login, encoded_password)
    if result is None:
        Info.count += 1
        if Info.count == 3:
            await message.answer(
                text="Неверный пароль. Ты заблокирован на 60 секунд."
            )
            user_id = message.from_user.id
            await Repo.insert_into_visited_date(user_id, "Три неудачных попытки авторизации")
            await asyncio.sleep(60)
            await message.answer(
                text="нажми /start"
            )
            Info.count = 0
            await state.clear()
            return
    if result:
        user_payload = {
            'login': result.login,
            'name': result.name,
            'status': result.status,
        }
        token = await create_jwt_token(user_payload)
        await Repo.insert_into_visited_date(result.name, "зашёл в чат")
        await state.clear()
        await state.update_data(jwt_token=token)
        await message.answer(
            text=f"Добро пожаловать, {result.name}!\nТеперь можешь написать /help."
        )
        return
    await message.answer(text="Не зашло с паролем :(")
    await state.set_state(AuthStates.waiting_for_login)


@dp.message(Command("help"))
@token_required
async def cmd_start(message: types.Message, state: FSMContext):
    """help"""
    await message.answer(*lists.send)


@dp.message(Command("send"))
@token_required
async def cmd_send_photo(message: Message, command: CommandObject, state: FSMContext):
    """Select route for loading and create directory if Ok"""
    if command.args is None:
        await message.answer(
            "Ошибка: не переданы аргументы"
        )
        return
    try:
        Info.form, Info.city, Info.street, Info.home, Info.apartment = command.args.split("/", maxsplit=4)
        if Info.city not in lists.city:
            await message.answer(
                f"Ошибка: неправильный формат города : {Info.city}"
            )
            return
    except ValueError:
        await message.answer(
            "Ошибка: неправильный формат команды. Пример:\n"
            "/send fttx/Город/улица/дом/квартира(для ТО, подьезд/подвал, техэтаж, (иное))"
        )
        return
    dir_name = ""
    if Info.form == "fttx":
        dir_name = f"photos/fttx/{Info.city}/{Info.street}/{Info.home}/{Info.apartment}"
    if Info.form == "to":
        dir_name = f"photos/to/{Info.city}/{Info.street}/{Info.home}/{Info.apartment}"    #aparnment == entrance
    if Info.form == "FTTX":
        dir_name = f"photos/FTTX/{Info.city}/{Info.street}/{Info.home}/{Info.apartment}"    #aparnment == entrance
    if (any(c in r'/\:*?"<>|' for c in Info.apartment) or any(c in r'/\:*?"<>|' for c in Info.home) or
            any(c in r'/\:*?"<>|' for c in Info.street) or any(c in r'/\:*?"<>|' for c in Info.city)):
        await message.reply("Недопустимое имя директории!")
        return
    process = await asyncio.create_subprocess_shell(f"mkdir -p {dir_name}", stdout=subprocess.PIPE,
                                                    stderr=subprocess.PIPE)
    stdout, stderr = await process.communicate()
    if process.returncode == 0:
        await message.reply(f"Директория '{dir_name}' существует.")
    else:
        error_message = stderr.decode().strip() or "Ошибка при создании директории."
        await message.reply(f"Ошибка: {error_message}")
        return
    await message.answer(
        f"Фото будут загружен в {Info.city}/{Info.street}/{Info.home}/{Info.apartment}\n"
        f"Выберите и отправьте фотографии"
    )

    data = await state.get_data()
    token = data.get("jwt_token")
    if not token:
        await message.answer("Нет токена. Пройдите авторизацию через /start.")
        return

    decoded_data = await decode_jwt_token(token)
    full_name = decoded_data.get("name") if decoded_data else None
    await Repo.insert_into_visited_date(full_name,
                                        f"Добавил фото в "
                                        f"{Info.form}/{Info.city}/{Info.street}/{Info.home}/{Info.apartment}")

@dp.message(F.photo)
@token_required
async def view_3(msg: Message, state: FSMContext):
    """download photo"""
    await bot.download(
        msg.photo[-1],
        destination=f"{os.getcwd()}/photos/{Info.form}/{Info.city}/{Info.street}/{Info.home}/"
                    f"{Info.apartment}/{msg.photo[-1].file_id}+{msg.date}.jpg"
    )
    return

@dp.message(Command("view"))
@token_required
async def send_photo(message: types.Message, command: CommandObject, state: FSMContext):
    """view photo in directory"""
    if command.args is None:
        await message.answer(
            "Ошибка: не переданы аргументы"
        )
        return
    try:
        Info.form, Info.city, Info.street, Info.home, Info.apartment = command.args.split("/", maxsplit=4)
        images_folder = f'photos/{Info.form}/{Info.city}/{Info.street}/{Info.home}/{Info.apartment}/'
        if Info.city not in lists.city:
            await message.answer(
                f"Ошибка: неправильный формат города : {Info.city}"
            )
            return
    except ValueError:
        await message.answer(
            "Ошибка: неправильный формат команды. Пример:\n"
            "/send fttx/Город/улица/дом/квартира(для ТО, подьезд/подвал,чердак)"
        )
        return

    data = await state.get_data()
    token = data.get("jwt_token")
    if not token:
        await message.answer("Нет токена. Пройдите авторизацию через /start.")
        return

    decoded_data = await decode_jwt_token(token)
    full_name = decoded_data.get("name") if decoded_data else None

    await Repo.insert_into_visited_date(
        full_name,
        f"Посмотрел фото в {Info.form}/{Info.city}/{Info.street}/{Info.home}/{Info.apartment}"
    )

    if not os.path.isdir(images_folder):
        await message.answer(
            "Запрашиваемая директория отсутствует.\nНабери /help"
        )
        return

    images = [f for f in os.listdir(images_folder) if f.endswith(('jpg', 'jpeg', 'png', 'gif'))]
    if images:
        for row in images:
            with open(os.path.join(images_folder, row), 'rb') as file:
                 photo = BufferedInputFile(file.read(), 'uploaded_photo')
            await message.answer_photo(photo)
    else:
        await message.reply("В папке нет изображений.\nНабери /help")
    return

@dp.message(Command("exit"))
async def cmd_logout(message: types.Message, state: FSMContext):
    """exit"""
    await state.clear()
    await message.answer("Вы вышли из системы. Чтобы снова войти, используйте /start.")


async def main():
    """start"""
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
