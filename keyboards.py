from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def make_row_keyboard(items):
    """Создает клавиатуру с одной строкой кнопок."""
    buttons = [KeyboardButton(text=item) for item in items]
    return ReplyKeyboardMarkup(keyboard=[buttons], resize_keyboard=True, one_time_keyboard=True)