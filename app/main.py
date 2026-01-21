# Точка входа Telegram бота для изучения английских слов

import sys
import os

# Добавляем корневую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings

# Проверяем наличие токена
if not settings.BOT_TOKEN:
    print('Ошибка: TELEGRAM_TOKEN не установлен в .env файле')
    sys.exit(1)

# Импортируем бота
from bot.bot_instance import bot

# Импортируем все handlers для регистрации
from bot.handlers import start
from bot.handlers import learning
from bot.handlers import stats
from bot.handlers import words
from bot.handlers import favorites


def main():
    """Главная функция запуска бота."""
    print('=' * 50)
    print('Бот для изучения английских слов')
    print('=' * 50)
    print(f'Токен: {settings.BOT_TOKEN[:10]}...')
    print('Запуск бота...')

    try:
        # Удаляем вебхук, если был установлен
        bot.remove_webhook()

        # Запускаем polling
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        print('\nБот остановлен пользователем')
    except Exception as e:
        print(f'Ошибка: {e}')
        raise


if __name__ == '__main__':
    main()
