# Клавиатуры главного меню

from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from bot.states.learning_states import MenuButtons, CallbackData


def get_main_menu() -> ReplyKeyboardMarkup:
    """Создает клавиатуру главного меню.

    Returns:
        ReplyKeyboardMarkup: Клавиатура главного меню
    """
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton(MenuButtons.LEARN),
        KeyboardButton(MenuButtons.ADD_WORD)
    )
    keyboard.add(
        KeyboardButton(MenuButtons.FAVORITES),
        KeyboardButton(MenuButtons.STATS)
    )
    return keyboard


def get_back_menu() -> ReplyKeyboardMarkup:
    """Создает клавиатуру с кнопкой "Назад".

    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопкой назад
    """
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(MenuButtons.BACK))
    return keyboard


def get_cancel_menu() -> ReplyKeyboardMarkup:
    """Создает клавиатуру отмены (используется при вводе данных).

    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопкой отмены
    """
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(MenuButtons.BACK))
    return keyboard


def get_inline_back_to_menu() -> InlineKeyboardMarkup:
    """Создает inline кнопку возврата в меню.

    Returns:
        InlineKeyboardMarkup: Inline клавиатура
    """
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton('◀️ В меню', callback_data=CallbackData.BACK_TO_MENU))
    return keyboard
