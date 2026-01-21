# Handler избранного

from bot.bot_instance import bot
from bot.states.learning_states import MenuButtons, CallbackData
from bot.keyboards.main_menu import get_main_menu
from bot.keyboards.learning_kb import get_word_card_keyboard
from sql_db.db_init import get_session
from sql_db.sql_requests.users import get_user
from sql_db.sql_requests.words import get_user_favorites, remove_word_from_user_list


@bot.message_handler(func=lambda msg: msg.text == MenuButtons.FAVORITES)
def handle_favorites(message):
    """Обработчик кнопки "Избранное".

    Показывает все слова пользователя:
    - Личные слова (owner_user = user_id)
    - Глобальные слова в избранном (UserFavorite)
    """
    user_tg_id = message.from_user.id
    username = message.from_user.username or f'user_{user_tg_id}'

    with get_session() as session:
        user_id = get_user(session, user_nickname=username)

        if user_id is None:
            bot.send_message(
                message.chat.id,
                'Сначала выполните команду /start для регистрации.',
                reply_markup=get_main_menu()
            )
            return

        favorites = get_user_favorites(session, user_id)

    if not favorites:
        bot.send_message(
            message.chat.id,
            '⭐ У вас пока нет избранных слов.\n\n'
            'Нажмите "Добавить слово", чтобы добавить своё слово,\n'
            'или во время обучения нажимайте "В избранное"!',
            reply_markup=get_main_menu()
        )
        return

    # Считаем личные и глобальные слова
    user_words_count = sum(1 for w in favorites if w.get('is_user_word'))
    global_words_count = len(favorites) - user_words_count

    # Формируем заголовок
    header_parts = []
    if user_words_count > 0:
        header_parts.append(f'📝 {user_words_count} ваших')
    if global_words_count > 0:
        header_parts.append(f'⭐ {global_words_count} из словаря')

    header_text = f'*Избранное* ({len(favorites)} шт.)\n{" + ".join(header_parts)}'
    bot.send_message(message.chat.id, header_text, parse_mode='Markdown')

    for word in favorites[:20]:  # Показываем первые 20 слов
        # Иконка в зависимости от типа слова
        icon = '📝' if word.get('is_user_word') else '⭐'

        word_text = f"{icon} *{word['word_en']}*"
        if word.get('transcription'):
            word_text += f" [{word['transcription']}]"
        word_text += f" — {word['word_ru']}"

        keyboard = get_word_card_keyboard(word['translate_id'])

        bot.send_message(
            message.chat.id,
            word_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    if len(favorites) > 20:
        bot.send_message(
            message.chat.id,
            f'...и ещё {len(favorites) - 20} слов',
            reply_markup=get_main_menu()
        )
    else:
        bot.send_message(
            message.chat.id,
            'Это все ваши слова.',
            reply_markup=get_main_menu()
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith(CallbackData.REMOVE_WORD))
def handle_remove_word(call):
    """Обработчик удаления слова из избранного/личного списка."""
    user_tg_id = call.from_user.id
    username = call.from_user.username or f'user_{user_tg_id}'

    translate_id = int(call.data.replace(CallbackData.REMOVE_WORD, ''))

    with get_session() as session:
        user_id = get_user(session, user_nickname=username)

        if user_id is None:
            bot.answer_callback_query(call.id, 'Ошибка: пользователь не найден')
            return

        result = remove_word_from_user_list(session, user_id, translate_id)

    if result['success']:
        bot.answer_callback_query(call.id, '🗑️ ' + result['message'])
        # Удаляем сообщение со словом
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
    else:
        bot.answer_callback_query(call.id, result['message'])
