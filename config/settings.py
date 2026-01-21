# Конфигурация приложения

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Класс настроек приложения"""

    # Telegram Bot
    BOT_TOKEN: str = os.getenv('TELEGRAM_TOKEN', '')

    # Database
    POSTGRES_HOST: str = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT: str = os.getenv('POSTGRES_PORT', '5432')
    POSTGRES_DB: str = os.getenv('POSTGRES_DB', 'appdb')
    POSTGRES_USER: str = os.getenv('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD: str = os.getenv('POSTGRES_PASSWORD', '')

    # Learning settings
    WORDS_PER_SESSION: int = 20  # Количество слов в цикле обучения
    STREAK_TO_MEMORIZE: int = 5  # Количество правильных ответов для запоминания
    RESET_DAYS: int = 5  # Дней неактивности для сброса прогресса


settings = Settings()
