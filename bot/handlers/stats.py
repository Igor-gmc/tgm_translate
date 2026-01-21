# Handler статистики пользователя

from bot.bot_instance import bot
from bot.states.learning_states import MenuButtons
from bot.keyboards.main_menu import get_main_menu
from sql_db.db_init import get_session
from sql_db.sql_requests.users import get_user
from sql_db.sql_requests.learning import get_user_stats


@bot.message_handler(func=lambda msg: msg.text == MenuButtons.STATS)
def handle_stats(message):
    """Обработчик кнопки "Статистика"."""
    show_stats(message)


@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    """Обработчик команды /stats."""
    show_stats(message)


def show_stats(message):
    """Показывает статистику пользователя.

    Args:
        message: Сообщение от пользователя
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

        stats = get_user_stats(session, user_id)

    # Формируем текст статистики
    stats_text = (
        '📊 *Твоя статистика*\n\n'
        f'✅ Выучено слов: *{stats["memorized_count"]}*\n'
        f'📚 В процессе изучения: *{stats["in_progress_count"]}*\n\n'
        f'📝 Всего попыток: *{stats["total_attempts"]}*\n'
        f'✔️ Правильных: *{stats["correct_attempts"]}*\n'
        f'🎯 Точность: *{stats["accuracy"]}%*\n\n'
        f'➕ Твоих слов: *{stats["user_words_count"]}*\n'
        f'⭐ В избранном: *{stats["favorites_count"]}*'
    )

    # Добавляем мотивационное сообщение
    if stats['memorized_count'] == 0:
        stats_text += '\n\n💪 Начни учить слова, и здесь появится твой прогресс!'
    elif stats['memorized_count'] < 10:
        stats_text += '\n\n🌱 Хорошее начало! Продолжай в том же духе!'
    elif stats['memorized_count'] < 50:
        stats_text += '\n\n🌿 Отличный прогресс! Так держать!'
    elif stats['memorized_count'] < 100:
        stats_text += '\n\n🌳 Впечатляет! Ты на правильном пути!'
    else:
        stats_text += '\n\n🏆 Невероятно! Ты настоящий мастер!'

    bot.send_message(
        message.chat.id,
        stats_text,
        parse_mode='Markdown',
        reply_markup=get_main_menu()
    )
