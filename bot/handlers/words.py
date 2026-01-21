# Handler добавления слов пользователя

from bot.bot_instance import bot, get_user_state, set_user_state, clear_user_state
from bot.states.learning_states import States, MenuButtons
from bot.keyboards.main_menu import get_main_menu, get_cancel_menu
from sql_db.db_init import get_session
from sql_db.sql_requests.users import get_user
from sql_db.sql_requests.words import add_user_word


@bot.message_handler(func=lambda msg: msg.text == MenuButtons.ADD_WORD)
def handle_add_word(message):
    """Обработчик кнопки "Добавить слово"."""
    user_tg_id = message.from_user.id

    set_user_state(user_tg_id, States.ADD_WORD_EN)

    bot.send_message(
        message.chat.id,
        '➕ *Добавление слова в избранное*\n\n'
        'Введите английское слово:',
        parse_mode='Markdown',
        reply_markup=get_cancel_menu()
    )


@bot.message_handler(func=lambda msg: get_user_state(msg.from_user.id) and
                     get_user_state(msg.from_user.id)['state'] == States.ADD_WORD_EN)
def handle_word_en_input(message):
    """Обработчик ввода английского слова."""
    user_tg_id = message.from_user.id
    text = message.text.strip()

    # Проверка на команду отмены
    if text == MenuButtons.BACK:
        clear_user_state(user_tg_id)
        set_user_state(user_tg_id, States.MAIN_MENU)
        bot.send_message(
            message.chat.id,
            'Добавление слова отменено.',
            reply_markup=get_main_menu()
        )
        return

    # Валидация английского слова
    if not text or len(text) > 40:
        bot.send_message(
            message.chat.id,
            '❌ Слово должно быть от 1 до 40 символов.\n'
            'Введите английское слово:',
            reply_markup=get_cancel_menu()
        )
        return

    # Сохраняем английское слово и переходим к вводу перевода
    set_user_state(user_tg_id, States.ADD_WORD_RU, {'word_en': text})

    bot.send_message(
        message.chat.id,
        f'Английское слово: *{text}*\n\n'
        'Теперь введите русский перевод:',
        parse_mode='Markdown',
        reply_markup=get_cancel_menu()
    )


@bot.message_handler(func=lambda msg: get_user_state(msg.from_user.id) and
                     get_user_state(msg.from_user.id)['state'] == States.ADD_WORD_RU)
def handle_word_ru_input(message):
    """Обработчик ввода русского перевода."""
    user_tg_id = message.from_user.id
    username = message.from_user.username or f'user_{user_tg_id}'
    text = message.text.strip()

    state = get_user_state(user_tg_id)

    # Проверка на команду отмены
    if text == MenuButtons.BACK:
        clear_user_state(user_tg_id)
        set_user_state(user_tg_id, States.MAIN_MENU)
        bot.send_message(
            message.chat.id,
            'Добавление слова отменено.',
            reply_markup=get_main_menu()
        )
        return

    # Валидация русского слова
    if not text or len(text) > 250:
        bot.send_message(
            message.chat.id,
            '❌ Перевод должен быть от 1 до 250 символов.\n'
            'Введите русский перевод:',
            reply_markup=get_cancel_menu()
        )
        return

    word_en = state['data']['word_en']

    # Добавляем слово в базу
    with get_session() as session:
        user_id = get_user(session, user_nickname=username)

        if user_id is None:
            bot.send_message(
                message.chat.id,
                'Ошибка: пользователь не найден. Выполните /start',
                reply_markup=get_main_menu()
            )
            return

        result = add_user_word(session, user_id, word_en, text)

    clear_user_state(user_tg_id)
    set_user_state(user_tg_id, States.MAIN_MENU)

    if result['success']:
        if result['is_global']:
            # Слово найдено в глобальном словаре и добавлено в избранное
            bot.send_message(
                message.chat.id,
                f'⭐ Слово найдено в словаре!\n\n'
                f'*{word_en}* — {text}\n\n'
                'Добавлено в избранное.',
                parse_mode='Markdown',
                reply_markup=get_main_menu()
            )
        else:
            # Создано новое личное слово
            bot.send_message(
                message.chat.id,
                f'✅ Слово добавлено!\n\n'
                f'*{word_en}* — {text}\n\n'
                'Теперь оно будет появляться в обучении.',
                parse_mode='Markdown',
                reply_markup=get_main_menu()
            )
    else:
        # Слово уже существует
        bot.send_message(
            message.chat.id,
            f'⚠️ {result["message"]}:\n'
            f'*{word_en}* — {text}',
            parse_mode='Markdown',
            reply_markup=get_main_menu()
        )
