import asyncio
import logging
from asyncio import sleep
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
import keyboards
from repository import Repo
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv('API_TOKEN')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class SelectInfo(StatesGroup):
    register_user = State()

class Info:
    form = None
    city = None
    street = None
    home = None
    apartment = None

class Registred:
    admin_OK = False
    user_OK = False
    login = None
    name = None
    count = 0

@dp.message(StateFilter(None), Command("start"))
async def start_handler(msg: Message, state=FSMContext):
    await msg.answer("Привет! \n")
    await msg.answer(
        text="Знаешь как зайти? :)",
        reply_markup=keyboards.make_row_keyboard(['xxxxx'])
    )
    await state.set_state(SelectInfo.register_user)

# ввод и проверка пароля
@dp.message(SelectInfo.register_user)
async def cmd_auth(msg: Message, state: FSMContext):
    if Registred.count > 3:
        Registred.count = 0
    autent = msg.text.split('|')
    if len(autent) != 2:
        Registred.count += 1
        await msg.answer(
            text=f"Что то за не то с паролем :("
        )
        if Registred.count == 3:
            await msg.answer(
                text="Теперь ждём минуту :("
            )
            await Repo.insert_into_visited_date(msg.from_user.id, f"{msg.from_user.id} три некорректные авторизации :)")
            await sleep(60)
        return
    else:
        Registred.count += 1
        auth = msg.text.split("|")
        login = auth[0]
        password = auth[1]
        pass_wrd = password.encode('utf-8')
        password = base64.b64encode(pass_wrd)
        if len(login) == 0 or len(password) < 7:
            await msg.answer(
                text=f"Что то не получилось с паролем :("
            )
            if Registred.count == 3:
                await msg.answer(
                    text="Теперь ждём минуту :("
                )
                await Repo.insert_into_visited_date(msg.from_user.id, f"{msg.from_user.id} три неверных пароля :)")
                await sleep(60)
            await state.clear()
            return
        else:
            result = await Repo.select_pass(login, password, msg.from_user.id)
            if result is None:
                await msg.answer(
                    text=f"Не зашло с паролем :("
                )
                Registred.count += 1
                if Registred.count == 3:
                    await msg.answer(
                        text="Теперь ждём минуту :("
                    )
                    await Repo.insert_into_visited_date(msg.from_user.id, f"{msg.from_user.id} три хаотичных пароля :)")
                    await sleep(60)
                    await state.clear()
                    return
            else:
                if result.tg_id not in lists.access:
                    await msg.answer(
                        text=f"Упс. Что то не так с данными :("
                    )
                    return
                if result.status == "admin":
                    Registred.admin_OK = True
                if result.tg_id in lists.access:
                    Registred.user_OK = True
                    Registred.login = result.login
                    Registred.name = result.name
                    await Repo.insert_into_visited_date(Registred.name, f"зашёл в чат загрузки фото fttx ")
                await msg.answer(
                    text=f"Набери\n/help, {result.name}"
                )
                await bot.send_message(os.getenv("admin_id"), 'В бот зашёл ' + result.name)
                await state.clear()
                return

@dp.message(Command("help"))
async def cmd_start(message: types.Message):
    if Registred.login not in lists.id_user and Registred.user_OK is False:
        await message.answer(
            text=f"Увы. Нет доступа к внутренней информации :("
        )
        return
    else:
        await message.answer(*lists.send)

@dp.message(Command("send"))
async def cmd_send_photo(
        message: Message,
        command: CommandObject
):
    if Registred.login not in lists.id_user and Registred.user_OK is False:
        await message.answer(
            text=f"Увы. Нет доступа к внутренней информации :("
        )
        return
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
            "/send fttx/Город/улица/дом/квартира(для ТО, подьезд/подвал,чердак)"
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
    await Repo.insert_into_visited_date(Registred.name,
                                        f"Добавил фото в "
                                        f"{Info.form}/{Info.city}/{Info.street}/{Info.home}/{Info.apartment}")

@dp.message(F.photo)
async def view_3(msg: Message, state: FSMContext):
    if Registred.login not in lists.id_user and Registred.user_OK is False:
        await msg.answer(
            text=f"Увы. Нет доступа к внутренней информации :("
        )
        await state.clear()
        return
    if Info.city is None:
        await msg.reply(f"Ошибка: не указан адрес")
        await state.clear()
        return

    await bot.download(
        msg.photo[-1],
        destination=f"{os.getcwd()}/photos/{Info.form}/{Info.city}/{Info.street}/{Info.home}/"
                    f"{Info.apartment}/{msg.photo[-1].file_id}+{msg.date}.jpg"
    )
    await state.clear()
    return

@dp.message(Command("view"))
async def send_photo(message: types.Message, command: CommandObject):
    if Registred.login not in lists.log_admin and Registred.admin_OK is False:
        await message.answer(
            text=f"Нет доступа к внутренней информации. Требуются расширенные права"
        )
        return
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
    await Repo.insert_into_visited_date(Registred.name,
                                        f"Посмотрел фото в "
                                        f"{Info.form}/{Info.city}/{Info.street}/{Info.home}/{Info.apartment}")
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

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

