# Создание экземпляра Telegram бота

import telebot
from config.settings import settings

# Создаем экземпляр бота
bot = telebot.TeleBot(settings.BOT_TOKEN)

# Хранилище состояний пользователей
# Формат: {user_id: {'state': 'learning', 'data': {...}}}
user_states = {}


def get_user_state(user_id: int) -> dict | None:
    """Получает состояние пользователя.

    Args:
        user_id (int): Telegram ID пользователя

    Returns:
        dict | None: Состояние пользователя или None
    """
    return user_states.get(user_id)


def set_user_state(user_id: int, state: str, data: dict = None):
    """Устанавливает состояние пользователя.

    Args:
        user_id (int): Telegram ID пользователя
        state (str): Название состояния
        data (dict): Дополнительные данные состояния
    """
    user_states[user_id] = {
        'state': state,
        'data': data or {}
    }


def clear_user_state(user_id: int):
    """Очищает состояние пользователя.

    Args:
        user_id (int): Telegram ID пользователя
    """
    if user_id in user_states:
        del user_states[user_id]


def update_user_data(user_id: int, **kwargs):
    """Обновляет данные в состоянии пользователя.

    Args:
        user_id (int): Telegram ID пользователя
        **kwargs: Данные для обновления
    """
    if user_id in user_states:
        user_states[user_id]['data'].update(kwargs)
