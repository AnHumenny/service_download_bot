import asyncio
from itertools import combinations

import jwt
import datetime
import hashlib
from functools import wraps
from aiogram import Bot, Dispatcher, types
import os

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import BufferedInputFile
from aiogram.filters import Command, StateFilter

import keyboards
from lists import lists, lists_admin

from schemas.repository import Repo
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

import logging

load_dotenv()
API_TOKEN = os.getenv('API_TOKEN')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

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


async def create_jwt_token(data):
    """Create token"""
    token = jwt.encode({
        **data,
        'exp': datetime.now(tz=timezone.utc) + timedelta(hours=2)
    }, os.getenv("SECRET_KEY"), algorithm='HS256')
    return token


async def decode_jwt_token(token):
    """Decode token"""
    try:
        decoded_data = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=['HS256'])
        return decoded_data
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(admin_only=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(message: types.Message, state: FSMContext, *args, **kwargs):
            data = await state.get_data()
            token = data.get("jwt_token")
            if not token:
                await message.answer("Нет сохранённого токена. Пройдите авторизацию через /start.")
                return None
            decoded_data = await decode_jwt_token(token)
            if not decoded_data:
                await message.answer("Токен недействителен или истёк. Авторизуйтесь снова.")
                return None
            status = decoded_data.get("status")
            if admin_only and status != "admin":
                await message.answer("Доступ запрещён. Требуются права администратора.")
                return None
            return await func(message, state=state, decoded_data=decoded_data, *args, **kwargs)
        return wrapper
    return decorator

@dp.message(StateFilter(None), Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    """Start(enter login)"""
    await state.set_state(AuthStates.waiting_for_login)
    await message.answer("Введите ваш логин:")


@dp.message(AuthStates.waiting_for_login)
async def process_login(message: types.Message, state: FSMContext):
    """Start(enter password)"""
    await state.update_data(username=message.text)
    await message.answer("Теперь введите пароль:")
    await state.set_state(AuthStates.waiting_for_password)


def hash_password(password: str) -> str:
    """Hashing password."""
    return hashlib.sha256(password.encode()).hexdigest()

@dp.message(AuthStates.waiting_for_login)
async def process_login(message: types.Message, state: FSMContext):
    """Start (enter password)"""
    await state.update_data(username=message.text)
    await message.answer("Теперь введите пароль:")
    await state.set_state(AuthStates.waiting_for_password)


@dp.message(AuthStates.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    """Authorization"""
    if message.text.startswith("/"):
        await message.answer("Пожалуйста, введите пароль, а не команду.")
        return

    user_data = await state.get_data()
    username = user_data.get('username')
    if not username:
        await message.answer("Ошибка: логин не найден. Нажмите /start для повторной авторизации.")
        await state.clear()
        return

    password = message.text
    tg_id = message.from_user.id
    encoded_password = hash_password(password)
    result = await Repo.select_pass(username, encoded_password, tg_id)

    if not result:
        Info.count += 1
        if Info.count == 3:
            await message.answer(
                text="Неверный пароль. Ты заблокирован на 60 секунд."
            )
            await asyncio.sleep(60)
            await message.answer(
                text="Нажми /start"
            )
            Info.count = 0
            await state.clear()
            return
        await message.answer(text="Не зашло с паролем :(")
        await state.set_state(AuthStates.waiting_for_login)
        return

    user_payload = {
        'login': result.login,
        'status': result.status,
        'tg_id': tg_id
    }

    token = await create_jwt_token(user_payload)
    await state.update_data(jwt_token=token)
    await state.set_state(None)

    if result.status == "admin":
        await message.answer(
            text=f"Добро пожаловать, администратор {result.login}!\n"
                 f"Напиши /admin_help для доступа к админ-командам или /help для общих команд."
        )
    else:
        await message.answer(
            text=f"Добро пожаловать, {result.login}!\n"
                 f"Напиши /help для списка доступных команд."
        )


@dp.message(Command("help"))
@token_required(admin_only=False)
async def help_command(message: types.Message, state: FSMContext, decoded_data: dict):
    """Help command for all users"""
    if isinstance(lists.send, list):
        response = "\n".join(lists.send)
    else:
        response = lists.send
    await message.answer(
        text=f"Команды для {decoded_data.get('login', 'Unknown')}:\n"
             f"{response}"
    )

@dp.message(Command("admin_help"))
@token_required(admin_only=True)
async def admin_help(message: types.Message, state: FSMContext, decoded_data: dict):
    """Admin help command"""
    if isinstance(lists_admin.send, list):
        response = "\n".join(lists.send) + "\n".join(lists_admin.send)
    else:
        response = lists.send
    await message.answer(
        text=f"Команды для {decoded_data.get('login', 'Unknown')}:\n"
             f"{response}"
    )


async def check_args(text: str) -> str:
    """Generates a path from the command arguments."""
    parts = text.split()[1:]
    if not parts:
        return ""
    return "/".join(parts)


@dp.message(Command("send"))
@token_required(admin_only=True)
async def check_simular(message: types.Message, state: FSMContext, decoded_data: dict):
    """Add new photos."""
    folders = [os.getenv('PATH_TO_FOLDER_1')]
    await message.answer(
        text="Выберите путь к папке загрузки:",
        reply_markup=keyboards.make_row_keyboard(folders)
    )
    await state.set_state(Operation.send_photo)


@dp.message(StateFilter(Operation.send_photo))
@token_required(admin_only=False)
async def send_photo(message: types.Message, state: FSMContext, decoded_data: dict):
    """Select route for loading and create directory if Ok"""
    folder_path = message.text.strip()

    try:
        parts = folder_path.split("/", maxsplit=4)
        if len(parts) != 5:
            raise ValueError("Недостаточно частей в пути")

        Info.form, Info.city, Info.street, Info.home, Info.apartment = parts

        if Info.city not in lists.city:
            await message.answer(f"Ошибка: неправильный формат города: {Info.city}")
            return

        if Info.form not in lists.err:
            await message.answer("Ошибка: выбран некорректный тип работ.")
            return

    except ValueError as e:
        await message.answer(
            "Ошибка: неправильный формат пути. Пример:\n"
            "Физ/Город/Улица/Дом/Квартира(для ТО, подъезд/подвал, техэтаж, (иное))"
        )
        return

    if any(c in r'/\:*?"<>|' for c in (Info.apartment + Info.home + Info.street + Info.city)):
        await message.reply("Недопустимое имя директории!")
        return

    check_arg = folder_path
    directory = f"photos/{check_arg}"

    try:
        os.makedirs(directory, exist_ok=True)
        await state.update_data(check_arg=check_arg)
        await message.reply(f"Директория '{directory}' создана или уже существует.")
    except PermissionError as e:
        await message.reply(f"Ошибка: нет прав для создания директории '{directory}': {str(e)}")
        return
    except OSError as e:
        await message.reply(f"Ошибка при создании директории '{directory}': {str(e)}")
        return
    except Exception as e:
        await message.reply(f"Неизвестная ошибка при создании директории: {str(e)}")
        return

    await message.answer(
        f"Фото будут загружены в {check_arg}\n"
        f"Выберите и отправьте фотографии"
    )
    await state.set_state(AuthStates.waiting_for_photos)


@dp.message(StateFilter(AuthStates.waiting_for_photos),
            lambda message: message.content_type == types.ContentType.PHOTO)
async def process_photo(message: types.Message, state: FSMContext):
    """Handle photo uploads"""
    data = await state.get_data()
    directory = f"photos/{data.get('check_arg')}"
    login = (await decode_jwt_token(data.get("jwt_token"))).get("login", "Unknown")\
        if data.get("jwt_token") else "Unknown"

    try:
        if not os.path.exists(directory):
            await message.answer(f"Ошибка: директория '{directory}' не существует")
            await state.clear()
            return

        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        file_path = f"{directory}/{photo.file_unique_id}.jpg"

        if not os.access(directory, os.W_OK):
            await message.answer(f"Ошибка: нет прав на запись в директорию '{directory}'")
            await state.clear()
            return

        await message.bot.download_file(file.file_path, file_path)
        await message.answer(f"Фотография сохранена в {file_path}")


    except Exception as e:
        await message.answer(f"Ошибка при сохранении фотографии: {str(e)}")
        return
    await state.update_data(check_arg=None, first_folder=None, second_folder=None)
    await state.set_state(AuthStates.waiting_for_photos)



@dp.message(Command("view"))
@token_required(admin_only=True)
async def check_simular(message: types.Message, state: FSMContext, decoded_data: dict):
    """Search for gas station by number."""
    folders = [os.getenv('PATH_TO_FOLDER_1')]
    await message.answer(
        text="Путь к папке: ",
        reply_markup=keyboards.make_row_keyboard(folders)
    )
    await state.set_state(Operation.view_photo)


@dp.message(StateFilter(Operation.view_photo))
@token_required(admin_only=True)
async def view_photo(message: types.Message, state: FSMContext, decoded_data: dict):
    """View photos in directory"""
    folder_path = message.text.strip()

    try:
        parts = folder_path.split("/", maxsplit=4)
        if len(parts) != 5:
            raise ValueError("Недостаточно частей в пути")

        form, city, street, home, apartment = parts

        if city not in lists.city:
            await message.answer(f"Ошибка: неправильный формат города: {city}")
            return

        if form not in lists.err:
            await message.answer("Ошибка: выбран некорректный тип работ.")
            return

    except ValueError as e:
        await message.answer(
            "Ошибка: неправильный формат пути. Пример:\n"
            "Физ/Город/Улица/Дом/Квартира(для ТО, подъезд/подвал, чердак)"
        )
        return

    if any(c in r'/\:*?"<>|' for c in (apartment + home + street + city + form)):
        await message.answer("Invalid characters in directory name!")
        return

    images_folder = f"photos/{folder_path}"

    if not os.path.isdir(images_folder):
        await message.answer("Запрашиваемая директория отсутствует.\nНабери /admin_help")
        return

    images = [f for f in os.listdir(images_folder) if f.lower().endswith(('jpg', 'jpeg', 'png', 'gif'))]
    if images:
        for image in images:
            try:
                with open(os.path.join(images_folder, image), 'rb') as file:
                    photo = BufferedInputFile(file.read(), filename=image)
                await message.answer_photo(photo)
            except Exception as e:
                await message.answer(f"Ошибка при просмотре фотографии: {str(e)}")
                await state.update_data(check_arg=None, first_folder=None, second_folder=None)
                await state.set_state(None)
                return

            await state.update_data(check_arg=None, first_folder=None, second_folder=None)
            await state.set_state(None)


def similar(a, b):
    """Сравнивает два имени файлов и возвращает True, если они идентичны."""
    return a.lower() == b.lower()


def find_similar_filenames(folders):
    """Searches for files with the same name in the specified folders."""
    all_files = []
    for folder in folders:
        try:
            if not os.path.isdir(folder):
                continue
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(('jpg', 'jpeg', 'png', 'gif')):
                        all_files.append((file, os.path.join(root, file)))
        except Exception as e:
            return e

    similar_pairs = []
    for (file1, path1), (file2, path2) in combinations(all_files, 2):
        if similar(file1, file2):
            similar_pairs.append((file1, path1, file2, path2))

    return similar_pairs


@dp.message(Command("simular"))
@token_required(admin_only=True)
async def check_simular(message: types.Message, state: FSMContext, decoded_data: dict):
    """Search simular filenames."""
    folders = [os.getenv('PATH_TO_FOLDER_1'), os.getenv('PATH_TO_FOLDER_2')]
    await message.answer(
        text="Выберите первую папку: ",
        reply_markup=keyboards.make_row_keyboard(folders)
    )
    await state.set_state(Simular.view_first_folder)


@dp.message(Command("check_simular_first"))
@token_required(admin_only=True)
async def check_simular_first(message: types.Message, state: FSMContext, decoded_data: dict):
    """Инициирует выбор первой папки для сравнения."""
    await state.update_data(check_arg=None, first_folder=None, second_folder=None)

    await message.answer(
        text="Введите маршрут к первой папке для сравнения :"
    )
    await state.set_state(Simular.view_first_folder)


@dp.message(StateFilter(Simular.view_first_folder))
async def select_second_folder(message: types.Message, state: FSMContext):
    """Processes the selection of the first folder and requests the second one."""
    first_folder = message.text.strip()

    try:
        parts = first_folder.split("/", maxsplit=4)
        if len(parts) != 5:
            raise ValueError("Недостаточно частей в пути")

        form, city, street, home, apartment = parts

        if city not in lists.city:
            await message.answer(f"Ошибка: неправильный формат города: {city}")
            return

        if form not in lists.err:
            await message.answer("Ошибка: выбран некорректный тип работ.")
            return

        if any(c in r'/\:*?"<>|' for c in (apartment + home + street + city + form)):
            await message.answer("Недопустимое имя директории!")
            return

    except ValueError as e:
        await message.answer(
            "Ошибка: неправильный формат пути. Пример:\n"
            "Физ/Город/Улица/Дом/Квартира(для ТО, подъезд/подвал, техэтаж, (иное))"
        )
        return

    await state.update_data(check_arg=None, first_folder=first_folder)

    await message.answer(
        text="Введите путь к второй папке для сравнения (в формате Физ/Город/Улица/Дом/Квартира):"
    )
    await state.set_state(Simular.view_second_folder)


@dp.message(StateFilter(Simular.view_second_folder))
async def process_folders(message: types.Message, state: FSMContext):
    """Processes the second folder and searches for similar files."""
    second_folder = message.text
    data = await state.get_data()
    first_folder = data.get("first_folder")

    if second_folder == first_folder:
        await message.answer(
            "Ошибка: вторая папка не должна совпадать с первой.",
            reply_markup=keyboards.make_row_keyboard(["маршруты папок совпадать не должны!"])
        )
        return

    folders = [f"photos/{first_folder}", f"photos/{second_folder}"]

    for folder in folders:
        if not os.path.isdir(folder):
            await message.answer(f"Ошибка: папка '{folder}' не существует.")
            return

    similar_pairs = find_similar_filenames(folders)

    if similar_pairs:
        response = "Найдены файлы с одинаковыми именами:\n"
        for file1, path1, file2, path2 in similar_pairs:
            response += f"- {file1} ({path1})\n  идентичен {file2} ({path2})\n********************"
        response += f"\n********************\nКоличество пар: {len(similar_pairs)}\n********************\n"
    else:
        response = "Файлов с одинаковыми именами не найдено."

    await message.answer(response)

    await state.update_data(check_arg=None, first_folder=None, second_folder=None)
    await state.set_state(None)


@dp.message(Command("exit"))
@token_required(admin_only=False)
async def cmd_logout(message: types.Message, state: FSMContext, decoded_data: dict = None):
    """Exit"""
    await state.clear()
    await message.answer("Вы вышли из системы. Чтобы снова войти, используйте /start.")


async def main():
    """start"""
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
