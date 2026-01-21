# Файл организации таблиц и связей таблиц

from datetime import datetime

from sqlalchemy import String, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

# Таблица пользователей Telegram
class User(Base):
    __tablename__ = 'user_tg'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_tg_nickname: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    translation: Mapped[list['Translate']] = relationship('Translate', back_populates='owner')

# Создаем таблицы данных пар слов и принадлежность к пользователю
class WordEn(Base):
    __tablename__='word_en'
    id: Mapped[int] = mapped_column(primary_key=True)
    word: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    transcription: Mapped[str] = mapped_column(String(255), unique=False, nullable=True)

    # одно английское слово может иметь несколько переводов
    translation: Mapped[list['Translate']] = relationship('Translate', back_populates='word_en')

class WordRu(Base):
    __tablename__='word_ru'
    id: Mapped[int] = mapped_column(primary_key=True)
    word: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)

    # одно русское слово может быть переводом нескольких английских
    translation: Mapped[list['Translate']] = relationship('Translate', back_populates='word_ru')

# Пары слово-перевод
# owner_user = NULL — главный словарь (из CSV), доступен всем
# owner_user = user_id — приватная пара, видит только владелец
class Translate(Base):
    __tablename__ = 'translate'
    __table_args__ = (
        UniqueConstraint('word_e', 'word_r', 'owner_user', name='uq_word_pair_owner'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    word_e: Mapped[int] = mapped_column(ForeignKey('word_en.id'), nullable=False)
    word_r: Mapped[int] = mapped_column(ForeignKey('word_ru.id'), nullable=False)
    # NULL = главный словарь, user_id = приватная пара пользователя
    owner_user: Mapped[int | None] = mapped_column(ForeignKey('user_tg.id'), default=None, nullable=True)

    word_en: Mapped['WordEn'] = relationship('WordEn', back_populates='translation')
    word_ru: Mapped['WordRu'] = relationship('WordRu', back_populates='translation')
    owner: Mapped['User'] = relationship('User', back_populates='translation')


# Избранное пользователя — пары из главного словаря, добавленные в личный список
# (только для пар с owner_user = NULL)
class UserFavorite(Base):
    __tablename__ = 'user_favorite'
    __table_args__ = (
        UniqueConstraint('user_id', 'translate_id', name='uq_user_favorite'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user_tg.id'), nullable=False)
    translate_id: Mapped[int] = mapped_column(ForeignKey('translate.id'), nullable=False)

    user: Mapped['User'] = relationship('User')
    translate: Mapped['Translate'] = relationship('Translate')



# Таблица прогресса изучения слов пользователем
# Цикл из 20 слов формируется так:
# 1. Обязательно: все приватные слова пользователя (Translate.owner_user = user_id)
# 2. Обязательно: все избранные слова (UserFavorite)
# 3. Дополняется рандомом из главного словаря до 20 слов
#
# Сброс прогресса: если is_memorized = False и прошло > 5 дней с last_attempt_at,
# то correct_streak сбрасывается на 0. Выученные слова (is_memorized = True) не сбрасываются.
class UserTranslationProgress(Base):
    __tablename__ = 'user_translation_progress'
    __table_args__ = (
        UniqueConstraint('user_id', 'translate_id', name='uq_user_translate'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user_tg.id'), nullable=False)
    translate_id: Mapped[int] = mapped_column(ForeignKey('translate.id'), nullable=False)

    # Счётчик правильных ответов подряд (0-5)
    correct_streak: Mapped[int] = mapped_column(default=0, nullable=False)
    # Слово выучено (True когда correct_streak достиг 5)
    is_memorized: Mapped[bool] = mapped_column(default=False, nullable=False)
    # Дата последней попытки (для сброса прогресса после 5 дней неактивности)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True)

    user: Mapped['User'] = relationship('User')
    translate: Mapped['Translate'] = relationship('Translate')


# Таблица учёта попыток перевода (история ответов)
class UserAttempt(Base):
    __tablename__ = 'user_attempts'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user_tg.id'), nullable=False)
    translate_id: Mapped[int] = mapped_column(ForeignKey('translate.id'), nullable=False)
    # Правильный ли был ответ
    is_correct: Mapped[bool] = mapped_column(nullable=False)
    # Время попытки
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped['User'] = relationship('User')
    translate: Mapped['Translate'] = relationship('Translate')
