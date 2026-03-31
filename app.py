import asyncio
from aiogram import Bot, Dispatcher, types, F
import os
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile
from aiogram.filters import Command, StateFilter
import keyboards
from lists import lists, lists_admin
from schemas.repository import Repo
from dotenv import load_dotenv
import logging
from utils.jwt_utils import create_jwt_token, token_required, decode_jwt_token
from utils.keyboard_utils import create_password_keyboard, create_letters_keyboard
from utils.password_utils import process_final_password, update_password_display, hash_password
from utils.storage import user_temp_passwords, AuthStates, Info, Operation, Simular

load_dotenv()
API_TOKEN = os.getenv('API_TOKEN')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


@dp.callback_query(F.data.startswith("pass_"), AuthStates.waiting_for_password)
async def process_password_input(callback: types.CallbackQuery, state: FSMContext):
    """Password entry processing via buttons."""
    user_id = callback.from_user.id
    full_data = callback.data
    action = full_data.split("_")[1]

    if user_id not in user_temp_passwords:
        user_temp_passwords[user_id] = ""

    if full_data.startswith("pass_mode_"):
        mode = full_data.split("_")[2]
        if mode == "digits":
            keyboard = create_password_keyboard(user_temp_passwords, user_id)
        elif mode == "letters":
            keyboard = await create_letters_keyboard("letters")
        elif mode == "caps":
            keyboard = await create_letters_keyboard("caps")

        masked_password = "•" * len(user_temp_passwords[user_id])
        await callback.message.edit_text(
            f"Введите пароль:\n\nПароль: {masked_password}",
            reply_markup=keyboard
        )
        await callback.answer()
        return

    if action == "back":
        user_temp_passwords[user_id] = user_temp_passwords[user_id][:-1]
    elif action == "enter":
        await process_final_password(callback, state)
        return
    elif action == "cancel":
        await callback.message.edit_text("❌ Ввод пароля отменен")
        await state.clear()
        if user_id in user_temp_passwords:
            del user_temp_passwords[user_id]
        return
    else:
        if len(user_temp_passwords[user_id]) < 20:
            symbol = action
            user_temp_passwords[user_id] += symbol

    await update_password_display(callback)


@dp.message(StateFilter(None), Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    """Start(enter login)"""
    await message.answer("Введите логин:")
    await state.set_state(AuthStates.waiting_for_login)


@dp.message(AuthStates.waiting_for_login)
async def process_login(message: types.Message, state: FSMContext):
    """Switching to entering the password via the keyboard."""
    await state.update_data(username=message.text)

    user_temp_passwords[message.from_user.id] = ""

    keyboard = create_password_keyboard(user_temp_passwords, message.from_user.id)
    await message.answer(
        "Теперь введите пароль используя кнопки ниже:\n\n"
        "Пароль: ••••••",
        reply_markup=keyboard
    )
    await state.set_state(AuthStates.waiting_for_password)


@dp.message(AuthStates.waiting_for_login)
async def process_login(message: types.Message, state: FSMContext):
    """Start(enter password)"""
    await state.update_data(username=message.text)
    await message.answer("Теперь введите пароль:")
    await state.set_state(AuthStates.waiting_for_password)


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
        await Repo.insert_into_visited_date(result.login, f"зашёл в бота", None)
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
        await Repo.insert_into_visited_date(login, f"Добавил фото в {file_path}", photo.file_unique_id)
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


@dp.message(Command("simular"))
@token_required(admin_only=True)
async def check_simular(message: types.Message, state: FSMContext, decoded_data: dict):
    """Search duplicate hash_name in database."""
    try:
        stats = await Repo.get_duplicate_statistics()

        if stats['duplicate_count'] == 0:
            await message.answer(
                "✅ **Дубликаты не найдены**\n\n"
                f"📊 Статистика:\n"
                f"• Всего записей: {stats['total_records']}\n"
                f"• Уникальных hash: {stats['unique_hashes']}"
            )
            return

        response = (
            f"🔍 **Найдено {stats['duplicate_count']} дубликатов**\n"
            f"📊 **Статистика:**\n"
            f"• Всего записей: {stats['total_records']}\n"
            f"• Уникальных hash: {stats['unique_hashes']}\n"
            f"• Дублирующихся записей: {stats['duplicate_records_count']}\n\n"
        )

        duplicates = await Repo.find_duplicate_hash_names()

        for i, dup in enumerate(duplicates, 1):
            response += f"📌 **Дубликат #{i}** (встречается {dup['count']} раз)\n"
            response += f"`hash: {dup['hash_name'][:40]}...`\n" if len(
                dup['hash_name']) > 40 else f"`hash: {dup['hash_name']}`\n"
            response += "**Записи:**\n"

            for j, record in enumerate(dup['records'], 1):
                response += f"  {j}. 👤 **{record['login']}**\n"
                response += f"     📅 {record['date_created'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                response += f"     📝 {record['action'][:80]}\n"
                if len(record['action']) > 80:
                    response += "...\n"
                response += "\n"

            response += "─" * 40 + "\n"

            if len(response) > 4000:
                await message.answer(response)
                response = ""

        if response:
            await message.answer(response)

    except Exception as e:
        await message.answer(f"❌ Ошибка при поиске дубликатов: {str(e)}")


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
