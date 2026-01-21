# Состояния пользователя в боте

class States:
    """Константы состояний пользователя"""

    # Главное меню
    MAIN_MENU = 'main_menu'

    # Режим обучения
    LEARNING = 'learning'
    LEARNING_ANSWER = 'learning_answer'

    # Добавление слова
    ADD_WORD_EN = 'add_word_en'
    ADD_WORD_RU = 'add_word_ru'

    # Просмотр избранного
    FAVORITES = 'favorites'

    # Статистика
    STATS = 'stats'


# Кнопки главного меню
class MenuButtons:
    """Текст кнопок меню"""

    LEARN = '📚 Учить слова'
    ADD_WORD = '➕ Добавить слово'
    FAVORITES = '⭐ Избранное'
    STATS = '📊 Статистика'
    BACK = '◀️ Назад'
    NEXT = '➡️ Дальше'
    ADD_TO_FAVORITES = '⭐ В избранное'
    REMOVE_WORD = '🗑️ Удалить'


# Callback data для inline кнопок
class CallbackData:
    """Префиксы для callback данных"""

    ANSWER = 'answer_'  # answer_translate_id_word
    FAVORITE_ADD = 'fav_add_'  # fav_add_translate_id
    REMOVE_WORD = 'rm_word_'  # rm_word_translate_id (удалить из избранного/личных)
    NEXT_WORD = 'next_word'
    BACK_TO_MENU = 'back_menu'
