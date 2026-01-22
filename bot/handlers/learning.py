# Handler режима обучения

import random
from bot.bot_instance import bot, get_user_state, set_user_state, update_user_data, clear_user_state
from bot.states.learning_states import States, MenuButtons, CallbackData
from bot.keyboards.main_menu import get_main_menu
from bot.keyboards.learning_kb import get_answer_keyboard, get_result_keyboard, get_learning_menu
from sql_db.db_init import get_session
from sql_db.sql_requests.users import get_user
from sql_db.sql_requests.learning import (
    get_words_for_learning, record_attempt, get_wrong_options, get_word_progress
)
from sql_db.sql_requests.words import is_word_in_favorites
from config.settings import settings


def send_word_question(chat_id: int, user_tg_id: int):
    """Отправляет следующий вопрос пользователю.

    Args:
        chat_id (int): ID чата
        user_tg_id (int): Telegram ID пользователя
    """
    state = get_user_state(user_tg_id)
    if state is None or state['state'] != States.LEARNING:
        return

    words = state['data'].get('words', [])
    current_index = state['data'].get('current_index', 0)

    # Проверяем, есть ли еще слова
    if current_index >= len(words):
        # Сессия завершена
        correct_count = state['data'].get('correct_count', 0)
        total_count = len(words)

        clear_user_state(user_tg_id)
        set_user_state(user_tg_id, States.MAIN_MENU)

        result_text = (
            f'🎉 Сессия завершена!\n\n'
            f'Правильных ответов: {correct_count}/{total_count}\n'
            f'Точность: {round(correct_count / total_count * 100) if total_count > 0 else 0}%\n\n'
            'Продолжай в том же духе! 💪'
        )

        bot.send_message(chat_id, result_text, reply_markup=get_main_menu())
        return

    # Получаем текущее слово
    current_word = words[current_index]
    translate_id = current_word['translate_id']

    # Получаем неправильные варианты
    with get_session() as session:
        wrong_options = get_wrong_options(session, translate_id, count=3)

    # Формируем текст вопроса (показываем русское слово)
    word_ru = current_word['word_ru']

    question_text = f'📖 Переведи слово:\n\n*{word_ru}*'
    question_text += f'\n\n_{current_index + 1} из {len(words)}_'

    # Создаем клавиатуру с ответами (английские варианты)
    keyboard = get_answer_keyboard(
        current_word['word_en'],
        wrong_options,
        translate_id
    )

    bot.send_message(
        chat_id,
        question_text,
        parse_mode='Markdown',
        reply_markup=keyboard
    )


@bot.message_handler(func=lambda msg: msg.text == MenuButtons.LEARN)
def handle_learn(message):
    """Обработчик кнопки "Учить слова"."""
    user_tg_id = message.from_user.id
    username = message.from_user.username or f'user_{user_tg_id}'

    with get_session() as session:
        user_id = get_user(session, user_nickname=username)

        if user_id is None:
            bot.send_message(
                message.chat.id,
                'Сначала выполните команду /start для регистрации.'
            )
            return

        # Получаем слова для обучения
        words = get_words_for_learning(session, user_id)

    if not words:
        bot.send_message(
            message.chat.id,
            'К сожалению, в базе нет слов для изучения.\n'
            'Добавьте свои слова или подождите обновления словаря.',
            reply_markup=get_main_menu()
        )
        return

    # Перемешиваем слова
    random.shuffle(words)

    # Устанавливаем состояние обучения
    set_user_state(user_tg_id, States.LEARNING, {
        'words': words,
        'current_index': 0,
        'correct_count': 0,
        'user_id': user_id
    })

    bot.send_message(
        message.chat.id,
        f'🎓 Начинаем обучение!\nСлов в сессии: {len(words)}',
        reply_markup=get_learning_menu()
    )

    # Отправляем первый вопрос
    send_word_question(message.chat.id, user_tg_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith(CallbackData.ANSWER))
def handle_answer(call):
    """Обработчик ответа на вопрос."""
    user_tg_id = call.from_user.id
    username = call.from_user.username or f'user_{user_tg_id}'

    state = get_user_state(user_tg_id)
    if state is None or state['state'] != States.LEARNING:
        bot.answer_callback_query(call.id, 'Сессия обучения не активна')
        return

    # Парсим callback data: answer_translateId_isCorrect
    parts = call.data.replace(CallbackData.ANSWER, '').split('_')
    translate_id = int(parts[0])
    is_correct = parts[1] == '1'

    words = state['data']['words']
    current_index = state['data']['current_index']
    current_word = words[current_index]

    # Проверяем, что ответ для текущего слова
    if current_word['translate_id'] != translate_id:
        bot.answer_callback_query(call.id, 'Ответ для другого слова')
        return

    with get_session() as session:
        user_id = get_user(session, user_nickname=username)

        # Записываем попытку
        result = record_attempt(session, user_id, translate_id, is_correct)

        # Проверяем, в избранном ли слово
        in_favorites = is_word_in_favorites(session, user_id, translate_id)

    # Обновляем счетчик правильных ответов
    if is_correct:
        update_user_data(user_tg_id, correct_count=state['data']['correct_count'] + 1)

    # Формируем сообщение с результатом
    word_en = current_word['word_en']
    word_ru = current_word['word_ru']
    transcription = current_word.get('transcription')
    is_user_word = current_word.get('is_user_word', False)

    if is_correct:
        result_emoji = '✅'
        result_text = 'Правильно!'

        if result['just_memorized']:
            result_text += '\n\n🎉 *Слово выучено!*'
        else:
            streak = result['correct_streak']
            remaining = settings.STREAK_TO_MEMORIZE - streak
            result_text += f'\n\nСерия: {streak}/{settings.STREAK_TO_MEMORIZE}'
            if remaining > 0:
                result_text += f' (ещё {remaining})'
    else:
        result_emoji = '❌'
        result_text = f'Неправильно!\n\nПравильный ответ: *{word_ru}*'
        result_text += '\n\nСерия сброшена'

    # Добавляем информацию о слове
    if transcription:
        word_info = f'\n\n{word_en} [{transcription}] — {word_ru}'
    else:
        word_info = f'\n\n{word_en} — {word_ru}'

    full_text = f'{result_emoji} {result_text}{word_info}'

    # Создаем клавиатуру с действиями
    keyboard = get_result_keyboard(translate_id, in_favorites, is_user_word)

    # Обновляем сообщение
    bot.edit_message_text(
        full_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown',
        reply_markup=keyboard
    )

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == CallbackData.NEXT_WORD)
def handle_next_word(call):
    """Обработчик кнопки "Дальше"."""
    user_tg_id = call.from_user.id

    state = get_user_state(user_tg_id)
    if state is None or state['state'] != States.LEARNING:
        bot.answer_callback_query(call.id, 'Сессия обучения не активна')
        return

    # Увеличиваем индекс текущего слова
    current_index = state['data']['current_index'] + 1
    update_user_data(user_tg_id, current_index=current_index)

    bot.answer_callback_query(call.id)

    # Удаляем предыдущее сообщение
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

    # Отправляем следующий вопрос
    send_word_question(call.message.chat.id, user_tg_id)


@bot.callback_query_handler(func=lambda call: call.data == CallbackData.BACK_TO_MENU)
def handle_back_to_menu(call):
    """Обработчик кнопки "В меню"."""
    user_tg_id = call.from_user.id

    clear_user_state(user_tg_id)
    set_user_state(user_tg_id, States.MAIN_MENU)

    bot.answer_callback_query(call.id)

    # Удаляем сообщение с кнопками
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

    bot.send_message(
        call.message.chat.id,
        'Главное меню:',
        reply_markup=get_main_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith(CallbackData.FAVORITE_ADD))
def handle_add_to_favorites(call):
    """Обработчик добавления в избранное (во время обучения)."""
    user_tg_id = call.from_user.id
    username = call.from_user.username or f'user_{user_tg_id}'

    translate_id = int(call.data.replace(CallbackData.FAVORITE_ADD, ''))

    with get_session() as session:
        from sql_db.sql_requests.words import add_to_favorites
        user_id = get_user(session, user_nickname=username)

        if user_id is None:
            bot.answer_callback_query(call.id, 'Ошибка: пользователь не найден')
            return

        success = add_to_favorites(session, user_id, translate_id)

    if success:
        bot.answer_callback_query(call.id, '⭐ Добавлено в избранное!')
    else:
        bot.answer_callback_query(call.id, 'Уже в избранном')
