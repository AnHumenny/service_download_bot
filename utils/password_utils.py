import asyncio
import hashlib
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from schemas.repository import Repo
from utils.jwt_utils import create_jwt_token
from utils.keyboard_utils import create_password_keyboard
from utils.storage import user_temp_passwords, AuthStates


def hash_password(password: str) -> str:
    """Hashihg password."""
    return hashlib.sha256(password.encode()).hexdigest()


class Info:
    """Class for storage info about tried access."""
    count = 0


async def process_final_password(callback: CallbackQuery, state: FSMContext):
    """Final password processing."""
    user_id = callback.from_user.id
    password = user_temp_passwords.get(user_id, "")

    if not password:
        await callback.answer("Пароль не может быть пустым!", show_alert=True)
        return

    if user_id in user_temp_passwords:
        del user_temp_passwords[user_id]

    user_data = await state.get_data()
    username = user_data.get('username')
    encoded_password = hash_password(password)

    tg_id = callback.from_user.id
    await callback.message.edit_reply_markup(reply_markup=None)

    result = await Repo.select_pass(username, encoded_password, tg_id)

    if result is None:
        Info.count += 1
        if Info.count == 3:
            await callback.message.answer(
                text="Неверный пароль. Ты заблокирован на 60 секунд."
            )
            await asyncio.sleep(60)
            await callback.message.answer(text="Нажми /start")
            Info.count = 0
            await state.clear()
            return
        else:
            await callback.message.answer(text=f"Неверный пароль. Осталось попыток: {3 - Info.count}")
            return

    if result:
        user_login = result.login if hasattr(result, 'login') else result.name

        user_payload = {
            'login': user_login,
            'status': result.status,
        }
        token = await create_jwt_token(user_payload)

        await state.clear()
        await state.update_data(
            jwt_token=token,
            status=result.status,
            chat_id=callback.message.chat.id,
            login=user_login
        )
        await callback.message.answer(
            text=f"Добро пожаловать, {user_login}!\nТеперь можешь написать /help."
        )
    else:
        await callback.message.answer(text="Ошибка авторизации.")
        await state.set_state(AuthStates.waiting_for_login)


async def update_password_display(callback: CallbackQuery):
    """Updates the masked password display."""
    user_id = callback.from_user.id
    current_password = user_temp_passwords.get(user_id, "")

    masked_password = "•" * len(current_password) if current_password else "••••••"

    keyboard = create_password_keyboard(user_temp_passwords, user_id)

    await callback.message.edit_text(
        f"Введите пароль используя кнопки ниже:\n\n"
        f"Пароль: {masked_password}",
        reply_markup=keyboard
    )
    await callback.answer()
