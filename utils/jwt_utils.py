import datetime
import os
from functools import wraps
import jwt
from aiogram import types
from aiogram.fsm.context import FSMContext


async def create_jwt_token(data):
    """Create token"""
    token = jwt.encode({
        **data,
        'exp': datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)
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


def token_required(admin_only: bool = True):
    """Check token and optionally admin status"""

    def decorator(func):
        @wraps(func)
        async def wrapper(message: types.Message, *args, **kwargs):
            state = kwargs.get('state')

            if not state:
                for arg in args:
                    if isinstance(arg, FSMContext):
                        state = arg
                        break

            if not state:
                await message.answer("Ошибка: состояние не найдено.")
                return None

            data = await state.get_data()
            token = data.get("jwt_token")
            status = data.get("status")

            if not token:
                await message.answer("Нет сохранённого токена. Пройдите авторизацию через /start.")
                return None

            if admin_only and status != "admin":
                await message.answer("Недостаточно прав доступа.")
                return None

            decoded_data = await decode_jwt_token(token)
            if decoded_data:
                import inspect
                sig = inspect.signature(func)

                if 'decoded_data' in sig.parameters:
                    return await func(message, *args, decoded_data=decoded_data, **kwargs)
                else:
                    return await func(message, *args, **kwargs)
            else:
                await message.answer("Токен недействителен или истёк. Авторизуйтесь снова.")
                return None

        return wrapper

    return decorator
