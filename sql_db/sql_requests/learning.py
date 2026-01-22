# Файл процесса обучения пользователя

# UserTranslationProgress — быстро отвечает на вопросы:
#     - "Выучил ли пользователь слово?"
#     - "Сколько правильных ответов подряд сейчас?"
#     - "Нужно ли сбросить прогресс?"
# UserAttempt — позволяет:
#     - Строить статистику обучения
#     - Анализировать историю ошибок
#     - Показывать графики прогресса

from datetime import datetime, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from sql_db.models import (
    Translate, WordEn, WordRu,
    UserTranslationProgress, UserAttempt, UserFavorite
)
from config.settings import settings


def get_or_create_progress(session: Session, user_id: int, translate_id: int) -> UserTranslationProgress:
    """Получает или создает запись прогресса для пары слов.

    Args:
        session (Session): Сессия подключения к БД
        user_id (int): id пользователя
        translate_id (int): id пары слов

    Returns:
        UserTranslationProgress: Объект прогресса
    """
    stmt = select(UserTranslationProgress).where(
        and_(
            UserTranslationProgress.user_id == user_id,
            UserTranslationProgress.translate_id == translate_id
        )
    )
    progress = session.execute(stmt).scalar_one_or_none()

    if progress is None:
        progress = UserTranslationProgress(
            user_id=user_id,
            translate_id=translate_id,
            correct_streak=0,
            is_memorized=False
        )
        session.add(progress)
        session.flush()

    return progress


def check_and_reset_stale_progress(session: Session, user_id: int) -> int:
    """Сбрасывает прогресс для слов с неактивностью более 5 дней.

    Сбрасывает только невыученные слова (is_memorized = False).
    Выученные слова (is_memorized = True) не сбрасываются.

    Args:
        session (Session): Сессия подключения к БД
        user_id (int): id пользователя

    Returns:
        int: Количество сброшенных записей прогресса
    """
    reset_threshold = datetime.utcnow() - timedelta(days=settings.RESET_DAYS)

    # Находим все записи с устаревшим прогрессом
    stmt = select(UserTranslationProgress).where(
        and_(
            UserTranslationProgress.user_id == user_id,
            UserTranslationProgress.is_memorized == False,
            UserTranslationProgress.last_attempt_at < reset_threshold,
            UserTranslationProgress.correct_streak > 0
        )
    )
    stale_progress = session.execute(stmt).scalars().all()

    reset_count = 0
    for progress in stale_progress:
        progress.correct_streak = 0
        reset_count += 1

    if reset_count > 0:
        session.flush()
        print(f'Сброшен прогресс для {reset_count} слов')

    return reset_count


def record_attempt(session: Session, user_id: int, translate_id: int, is_correct: bool) -> dict:
    """Записывает попытку перевода и обновляет прогресс.

    Args:
        session (Session): Сессия подключения к БД
        user_id (int): id пользователя
        translate_id (int): id пары слов
        is_correct (bool): Правильный ли был ответ

    Returns:
        dict: Информация о результате {
            'correct_streak': int,
            'is_memorized': bool,
            'just_memorized': bool  # True если слово только что выучено
        }
    """
    # Записываем попытку в историю
    attempt = UserAttempt(
        user_id=user_id,
        translate_id=translate_id,
        is_correct=is_correct,
        attempted_at=datetime.utcnow()
    )
    session.add(attempt)

    # Обновляем прогресс
    progress = get_or_create_progress(session, user_id, translate_id)
    progress.last_attempt_at = datetime.utcnow()

    just_memorized = False

    if is_correct:
        progress.correct_streak += 1
        # Проверяем, достигнут ли порог запоминания
        if progress.correct_streak >= settings.STREAK_TO_MEMORIZE and not progress.is_memorized:
            progress.is_memorized = True
            just_memorized = True
            print(f'Слово {translate_id} выучено!')
    else:
        # Сбрасываем streak при неправильном ответе
        progress.correct_streak = 0

    session.flush()

    return {
        'correct_streak': progress.correct_streak,
        'is_memorized': progress.is_memorized,
        'just_memorized': just_memorized
    }


def get_user_stats(session: Session, user_id: int) -> dict:
    """Получает статистику обучения пользователя.

    Args:
        session (Session): Сессия подключения к БД
        user_id (int): id пользователя

    Returns:
        dict: Статистика пользователя
    """
    # Общее количество попыток
    total_attempts = session.query(func.count(UserAttempt.id)).filter(
        UserAttempt.user_id == user_id
    ).scalar() or 0

    # Количество правильных ответов
    correct_attempts = session.query(func.count(UserAttempt.id)).filter(
        and_(
            UserAttempt.user_id == user_id,
            UserAttempt.is_correct == True
        )
    ).scalar() or 0

    # Количество выученных слов
    memorized_count = session.query(func.count(UserTranslationProgress.id)).filter(
        and_(
            UserTranslationProgress.user_id == user_id,
            UserTranslationProgress.is_memorized == True
        )
    ).scalar() or 0

    # Количество слов в процессе изучения (streak > 0, но не выучено)
    in_progress_count = session.query(func.count(UserTranslationProgress.id)).filter(
        and_(
            UserTranslationProgress.user_id == user_id,
            UserTranslationProgress.is_memorized == False,
            UserTranslationProgress.correct_streak > 0
        )
    ).scalar() or 0

    # Количество личных слов пользователя
    user_words_count = session.query(func.count(Translate.id)).filter(
        Translate.owner_user == user_id
    ).scalar() or 0

    # Количество избранных слов
    favorites_count = session.query(func.count(UserFavorite.id)).filter(
        UserFavorite.user_id == user_id
    ).scalar() or 0

    # Процент правильных ответов
    accuracy = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0

    return {
        'total_attempts': total_attempts,
        'correct_attempts': correct_attempts,
        'accuracy': round(accuracy, 1),
        'memorized_count': memorized_count,
        'in_progress_count': in_progress_count,
        'user_words_count': user_words_count,
        'favorites_count': favorites_count
    }


def get_words_for_learning(session: Session, user_id: int, limit: int = None) -> list[dict]:
    """Получает слова для обучения с учетом прогресса.

    Приоритет:
    1. Личные слова пользователя (owner_user = user_id)
    2. Избранные слова (UserFavorite)
    3. Случайные слова из главного словаря

    Исключает уже выученные слова (is_memorized = True).

    Args:
        session (Session): Сессия подключения к БД
        user_id (int): id пользователя
        limit (int): Максимальное количество слов

    Returns:
        list[dict]: Список слов для обучения
    """
    if limit is None:
        limit = settings.WORDS_PER_SESSION

    # Сначала сбрасываем устаревший прогресс
    check_and_reset_stale_progress(session, user_id)

    results = []
    used_ids = set()

    # Получаем ID выученных слов для исключения
    memorized_stmt = select(UserTranslationProgress.translate_id).where(
        and_(
            UserTranslationProgress.user_id == user_id,
            UserTranslationProgress.is_memorized == True
        )
    )
    memorized_ids = set(session.execute(memorized_stmt).scalars().all())

    # 1. Личные слова пользователя (не выученные)
    user_words_stmt = select(Translate).where(
        and_(
            Translate.owner_user == user_id,
            ~Translate.id.in_(memorized_ids) if memorized_ids else True
        )
    )
    user_words = session.execute(user_words_stmt).scalars().all()

    for word in user_words:
        if len(results) >= limit:
            break
        results.append({
            'translate_id': word.id,
            'word_en': word.word_en.word,
            'word_ru': word.word_ru.word,
            'transcription': word.word_en.transcription,
            'is_user_word': True
        })
        used_ids.add(word.id)

    # 2. Избранные слова (не выученные)
    if len(results) < limit:
        favorites_stmt = select(UserFavorite).where(
            and_(
                UserFavorite.user_id == user_id,
                ~UserFavorite.translate_id.in_(memorized_ids) if memorized_ids else True,
                ~UserFavorite.translate_id.in_(used_ids) if used_ids else True
            )
        )
        favorites = session.execute(favorites_stmt).scalars().all()

        for fav in favorites:
            if len(results) >= limit:
                break
            translate = fav.translate
            results.append({
                'translate_id': translate.id,
                'word_en': translate.word_en.word,
                'word_ru': translate.word_ru.word,
                'transcription': translate.word_en.transcription,
                'is_user_word': False
            })
            used_ids.add(translate.id)

    # 3. Случайные слова из главного словаря
    if len(results) < limit:
        remaining = limit - len(results)
        exclude_ids = used_ids | memorized_ids

        random_stmt = select(Translate).where(
            and_(
                Translate.owner_user.is_(None),
                ~Translate.id.in_(exclude_ids) if exclude_ids else True
            )
        ).order_by(func.random()).limit(remaining)

        random_words = session.execute(random_stmt).scalars().all()

        for word in random_words:
            results.append({
                'translate_id': word.id,
                'word_en': word.word_en.word,
                'word_ru': word.word_ru.word,
                'transcription': word.word_en.transcription,
                'is_user_word': False
            })

    return results


def get_word_progress(session: Session, user_id: int, translate_id: int) -> dict | None:
    """Получает прогресс изучения конкретного слова.

    Args:
        session (Session): Сессия подключения к БД
        user_id (int): id пользователя
        translate_id (int): id пары слов

    Returns:
        dict | None: Информация о прогрессе или None
    """
    progress = get_or_create_progress(session, user_id, translate_id)

    return {
        'correct_streak': progress.correct_streak,
        'is_memorized': progress.is_memorized,
        'last_attempt_at': progress.last_attempt_at
    }


def get_wrong_options(session: Session, correct_translate_id: int, count: int = 3) -> list[str]:
    """Получает неправильные варианты ответов для викторины.

    Args:
        session (Session): Сессия подключения к БД
        correct_translate_id (int): id правильной пары слов
        count (int): Количество неправильных вариантов

    Returns:
        list[str]: Список неправильных английских слов
    """
    # Получаем правильный перевод для исключения
    correct = session.get(Translate, correct_translate_id)
    if correct is None:
        return []

    correct_en_id = correct.word_e

    # Выбираем случайные английские слова, кроме правильного
    stmt = select(WordEn).where(
        WordEn.id != correct_en_id
    ).order_by(func.random()).limit(count)

    wrong_words = session.execute(stmt).scalars().all()

    return [word.word for word in wrong_words]


def reset_word_progress(session: Session, user_id: int, translate_id: int) -> bool:
    """Сбрасывает прогресс изучения конкретного слова.

    Args:
        session (Session): Сессия подключения к БД
        user_id (int): id пользователя
        translate_id (int): id пары слов

    Returns:
        bool: True если прогресс сброшен
    """
    stmt = select(UserTranslationProgress).where(
        and_(
            UserTranslationProgress.user_id == user_id,
            UserTranslationProgress.translate_id == translate_id
        )
    )
    progress = session.execute(stmt).scalar_one_or_none()

    if progress is None:
        return False

    progress.correct_streak = 0
    progress.is_memorized = False
    session.flush()
    return True
