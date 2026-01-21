# Клавиатуры для режима обучения

import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from bot.states.learning_states import MenuButtons, CallbackData


def get_answer_keyboard(correct_word: str, wrong_words: list[str],
                        translate_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру с вариантами ответов.

    Args:
        correct_word (str): Правильный ответ (русский перевод)
        wrong_words (list[str]): Список неправильных вариантов
        translate_id (int): id пары слов для проверки

    Returns:
        InlineKeyboardMarkup: Клавиатура с вариантами ответов
    """
    keyboard = InlineKeyboardMarkup(row_width=2)

    # Собираем все варианты и перемешиваем
    all_options = [(correct_word, True)] + [(w, False) for w in wrong_words]
    random.shuffle(all_options)

    # Создаем кнопки
    buttons = []
    for word, is_correct in all_options:
        callback_data = f'{CallbackData.ANSWER}{translate_id}_{1 if is_correct else 0}'
        buttons.append(InlineKeyboardButton(word, callback_data=callback_data))

    # Добавляем кнопки по 2 в ряд
    for i in range(0, len(buttons), 2):
        row = buttons[i:i + 2]
        keyboard.add(*row)

    return keyboard


def get_result_keyboard(translate_id: int, is_in_favorites: bool,
                        is_user_word: bool) -> InlineKeyboardMarkup:
    """Создает клавиатуру после ответа с действиями над словом.

    Args:
        translate_id (int): id пары слов
        is_in_favorites (bool): Слово в избранном (или личное слово)
        is_user_word (bool): Это личное слово пользователя

    Returns:
        InlineKeyboardMarkup: Клавиатура с действиями
    """
    keyboard = InlineKeyboardMarkup(row_width=2)

    # Кнопка "Дальше"
    next_btn = InlineKeyboardButton(MenuButtons.NEXT, callback_data=CallbackData.NEXT_WORD)

    # Кнопка добавления в избранное (только для глобальных слов, которых нет в избранном)
    if not is_user_word and not is_in_favorites:
        fav_btn = InlineKeyboardButton(
            MenuButtons.ADD_TO_FAVORITES,
            callback_data=f'{CallbackData.FAVORITE_ADD}{translate_id}'
        )
        keyboard.add(next_btn, fav_btn)
    else:
        keyboard.add(next_btn)

    # Кнопка возврата в меню
    keyboard.add(InlineKeyboardButton('◀️ В меню', callback_data=CallbackData.BACK_TO_MENU))

    return keyboard


def get_learning_menu() -> ReplyKeyboardMarkup:
    """Создает клавиатуру для режима обучения (reply).

    Returns:
        ReplyKeyboardMarkup: Клавиатура режима обучения
    """
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(MenuButtons.BACK))
    return keyboard


def get_word_card_keyboard(translate_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для карточки слова в избранном.

    Одна кнопка "Удалить" — удаляет слово из избранного
    (для личных слов — удаляет полностью, для глобальных — из UserFavorite).

    Args:
        translate_id (int): id пары слов

    Returns:
        InlineKeyboardMarkup: Клавиатура карточки слова
    """
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(
        MenuButtons.REMOVE_WORD,
        callback_data=f'{CallbackData.REMOVE_WORD}{translate_id}'
    ))
    return keyboard
