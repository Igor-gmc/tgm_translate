# Handler команды /start и регистрации пользователя

from bot.bot_instance import bot, set_user_state, clear_user_state
from bot.states.learning_states import States, MenuButtons
from bot.keyboards.main_menu import get_main_menu
from sql_db.db_init import get_session
from sql_db.sql_requests.users import get_or_create_user


@bot.message_handler(commands=['start'])
def cmd_start(message):
    """Обработчик команды /start.

    Регистрирует пользователя в БД (если новый) и показывает главное меню.
    """
    user_tg_id = message.from_user.id
    username = message.from_user.username or f'user_{user_tg_id}'

    with get_session() as session:
        user_id = get_or_create_user(session, username)

        if user_id is None:
            bot.send_message(
                message.chat.id,
                'Произошла ошибка при регистрации. Попробуйте позже.'
            )
            return

    # Устанавливаем состояние главного меню
    set_user_state(user_tg_id, States.MAIN_MENU)

    # Приветственное сообщение
    welcome_text = (
        f'Привет, {message.from_user.first_name}! 👋\n\n'
        'Я помогу тебе учить английские слова.\n\n'
        '📚 *Учить слова* — тренировка перевода\n'
        '➕ *Добавить слово* — добавить своё слово в избранное\n'
        '⭐ *Избранное* — твои слова и избранные из словаря\n'
        '📊 *Статистика* — твой прогресс\n\n'
        'Выбери действие:'
    )

    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=get_main_menu()
    )


@bot.message_handler(commands=['help'])
def cmd_help(message):
    """Обработчик команды /help."""
    help_text = (
        '*Как пользоваться ботом:*\n\n'
        '1️⃣ Нажми "Учить слова" для начала обучения\n'
        '2️⃣ Выбирай правильный перевод из 4 вариантов\n'
        '3️⃣ 5 правильных ответов подряд — слово выучено!\n\n'
        '*Особенности:*\n'
        '• Добавляй свои слова для изучения\n'
        '• Отмечай понравившиеся слова в избранное\n'
        '• Твои и избранные слова появляются чаще\n'
        '• Если не заходишь 5 дней — прогресс сбрасывается\n\n'
        '*Команды:*\n'
        '/start — начать сначала\n'
        '/help — эта справка\n'
        '/stats — статистика\n'
        '/menu — главное меню'
    )

    bot.send_message(
        message.chat.id,
        help_text,
        parse_mode='Markdown',
        reply_markup=get_main_menu()
    )


@bot.message_handler(commands=['menu'])
def cmd_menu(message):
    """Обработчик команды /menu — возврат в главное меню."""
    user_tg_id = message.from_user.id
    clear_user_state(user_tg_id)
    set_user_state(user_tg_id, States.MAIN_MENU)

    bot.send_message(
        message.chat.id,
        'Главное меню:',
        reply_markup=get_main_menu()
    )


@bot.message_handler(func=lambda msg: msg.text == MenuButtons.BACK)
def handle_back(message):
    """Обработчик кнопки "Назад" — возврат в главное меню."""
    cmd_menu(message)
