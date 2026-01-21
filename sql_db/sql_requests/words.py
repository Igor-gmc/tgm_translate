# Файл обработки слов и переводов

from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session

from sql_db.models import WordEn, WordRu, Translate, User, UserFavorite


def get_or_create_word_en(session: Session, word: str, transcription: str | None = None) -> int:
    """Получает или создает английское слово.

    Args:
        session (Session): Сессия подключения к БД
        word (str): Английское слово
        transcription (str | None): Транскрипция слова

    Returns:
        int: id слова в таблице word_en
    """
    word_lower = word.lower().strip()

    stmt = select(WordEn).where(WordEn.word == word_lower)
    word_obj = session.execute(stmt).scalar_one_or_none()

    if word_obj is not None:
        return word_obj.id

    # Создаем новое слово
    new_word = WordEn(word=word_lower, transcription=transcription)
    session.add(new_word)
    session.flush()
    return new_word.id


def get_or_create_word_ru(session: Session, word: str) -> int:
    """Получает или создает русское слово.

    Args:
        session (Session): Сессия подключения к БД
        word (str): Русское слово

    Returns:
        int: id слова в таблице word_ru
    """
    word_lower = word.lower().strip()

    stmt = select(WordRu).where(WordRu.word == word_lower)
    word_obj = session.execute(stmt).scalar_one_or_none()

    if word_obj is not None:
        return word_obj.id

    # Создаем новое слово
    new_word = WordRu(word=word_lower)
    session.add(new_word)
    session.flush()
    return new_word.id


def add_user_word(session: Session, user_id: int, word_en: str, word_ru: str,
                  transcription: str | None = None) -> dict:
    """Добавляет слово в избранное пользователя.

    Логика:
    1. Если пара слов есть в глобальном словаре (owner_user = NULL) → добавляем в избранное
    2. Если пары нет → создаем личную пару (owner_user = user_id)

    Args:
        session (Session): Сессия подключения к БД
        user_id (int): id пользователя
        word_en (str): Английское слово
        word_ru (str): Русский перевод
        transcription (str | None): Транскрипция (опционально)

    Returns:
        dict: {
            'success': bool,
            'translate_id': int | None,
            'is_global': bool,  # True если слово из глобального словаря
            'message': str
        }
    """
    # Получаем или создаем слова
    word_en_id = get_or_create_word_en(session, word_en, transcription)
    word_ru_id = get_or_create_word_ru(session, word_ru)

    # 1. Проверяем, есть ли такая пара в глобальном словаре
    stmt = select(Translate).where(
        and_(
            Translate.word_e == word_en_id,
            Translate.word_r == word_ru_id,
            Translate.owner_user.is_(None)
        )
    )
    global_pair = session.execute(stmt).scalar_one_or_none()

    if global_pair is not None:
        # Слово есть в глобальном словаре — добавляем в избранное
        # Проверяем, не добавлено ли уже
        fav_stmt = select(UserFavorite).where(
            and_(
                UserFavorite.user_id == user_id,
                UserFavorite.translate_id == global_pair.id
            )
        )
        existing_fav = session.execute(fav_stmt).scalar_one_or_none()

        if existing_fav is not None:
            return {
                'success': False,
                'translate_id': global_pair.id,
                'is_global': True,
                'message': 'Слово уже в избранном'
            }

        # Добавляем в избранное
        favorite = UserFavorite(user_id=user_id, translate_id=global_pair.id)
        session.add(favorite)
        session.flush()
        return {
            'success': True,
            'translate_id': global_pair.id,
            'is_global': True,
            'message': 'Слово найдено в словаре и добавлено в избранное'
        }

    # 2. Проверяем, нет ли уже такой личной пары у пользователя
    stmt = select(Translate).where(
        and_(
            Translate.word_e == word_en_id,
            Translate.word_r == word_ru_id,
            Translate.owner_user == user_id
        )
    )
    existing_user_pair = session.execute(stmt).scalar_one_or_none()

    if existing_user_pair is not None:
        return {
            'success': False,
            'translate_id': existing_user_pair.id,
            'is_global': False,
            'message': 'Это слово уже добавлено вами ранее'
        }

    # 3. Создаем новую личную пару
    new_translate = Translate(
        word_e=word_en_id,
        word_r=word_ru_id,
        owner_user=user_id
    )
    session.add(new_translate)
    session.flush()
    print(f'Добавлена личная пара слов: {new_translate.id}')
    return {
        'success': True,
        'translate_id': new_translate.id,
        'is_global': False,
        'message': 'Новое слово добавлено в ваш словарь'
    }


def find_word_in_db(session: Session, word: str, is_english: bool = True) -> list[dict]:
    """Ищет слово в базе данных.

    Args:
        session (Session): Сессия подключения к БД
        word (str): Слово для поиска
        is_english (bool): True для поиска английского слова, False для русского

    Returns:
        list[dict]: Список найденных пар с переводами
    """
    word_lower = word.lower().strip()
    results = []

    if is_english:
        stmt = select(Translate).join(WordEn).where(
            WordEn.word.ilike(f'%{word_lower}%')
        )
    else:
        stmt = select(Translate).join(WordRu).where(
            WordRu.word.ilike(f'%{word_lower}%')
        )

    pairs = session.execute(stmt).scalars().all()

    for pair in pairs:
        results.append({
            'translate_id': pair.id,
            'word_en': pair.word_en.word,
            'word_ru': pair.word_ru.word,
            'transcription': pair.word_en.transcription,
            'is_global': pair.owner_user is None
        })

    return results


def add_to_favorites(session: Session, user_id: int, translate_id: int) -> bool:
    """Добавляет пару слов в избранное пользователя.

    Можно добавлять только слова из главного словаря (owner_user = NULL).

    Args:
        session (Session): Сессия подключения к БД
        user_id (int): id пользователя
        translate_id (int): id пары слов из Translate

    Returns:
        bool: True если добавлено успешно, False при ошибке
    """
    # Проверяем, что пара существует и это глобальное слово
    translate = session.get(Translate, translate_id)
    if translate is None:
        print(f'Пара слов {translate_id} не найдена')
        return False

    if translate.owner_user is not None:
        print('Можно добавлять в избранное только слова из главного словаря')
        return False

    # Проверяем, нет ли уже в избранном
    stmt = select(UserFavorite).where(
        and_(
            UserFavorite.user_id == user_id,
            UserFavorite.translate_id == translate_id
        )
    )
    existing = session.execute(stmt).scalar_one_or_none()

    if existing is not None:
        print('Слово уже в избранном')
        return False

    # Добавляем в избранное
    favorite = UserFavorite(user_id=user_id, translate_id=translate_id)
    session.add(favorite)
    session.flush()
    print(f'Слово добавлено в избранное')
    return True


def remove_from_favorites(session: Session, user_id: int, translate_id: int) -> bool:
    """Удаляет пару слов из избранного пользователя.

    Args:
        session (Session): Сессия подключения к БД
        user_id (int): id пользователя
        translate_id (int): id пары слов из Translate

    Returns:
        bool: True если удалено успешно, False если не найдено
    """
    stmt = select(UserFavorite).where(
        and_(
            UserFavorite.user_id == user_id,
            UserFavorite.translate_id == translate_id
        )
    )
    favorite = session.execute(stmt).scalar_one_or_none()

    if favorite is None:
        print('Слово не найдено в избранном')
        return False

    session.delete(favorite)
    session.flush()
    print('Слово удалено из избранного')
    return True


def get_user_favorites(session: Session, user_id: int) -> list[dict]:
    """Получает список избранных слов пользователя.

    Включает:
    1. Глобальные слова, добавленные в избранное (UserFavorite)
    2. Личные слова пользователя (Translate с owner_user = user_id)

    Args:
        session (Session): Сессия подключения к БД
        user_id (int): id пользователя

    Returns:
        list[dict]: Список избранных пар слов с флагом is_user_word
    """
    results = []
    used_ids = set()

    # 1. Личные слова пользователя (owner_user = user_id)
    user_words_stmt = select(Translate).where(Translate.owner_user == user_id)
    user_words = session.execute(user_words_stmt).scalars().all()

    for pair in user_words:
        results.append({
            'translate_id': pair.id,
            'word_en': pair.word_en.word,
            'word_ru': pair.word_ru.word,
            'transcription': pair.word_en.transcription,
            'is_user_word': True  # Личное слово пользователя
        })
        used_ids.add(pair.id)

    # 2. Глобальные слова в избранном (UserFavorite)
    fav_stmt = select(UserFavorite).where(UserFavorite.user_id == user_id)
    favorites = session.execute(fav_stmt).scalars().all()

    for fav in favorites:
        if fav.translate_id not in used_ids:
            translate = fav.translate
            results.append({
                'translate_id': translate.id,
                'word_en': translate.word_en.word,
                'word_ru': translate.word_ru.word,
                'transcription': translate.word_en.transcription,
                'is_user_word': False  # Глобальное слово в избранном
            })

    return results


def get_user_words(session: Session, user_id: int) -> list[dict]:
    """Получает список личных слов пользователя (добавленных им самим).

    Args:
        session (Session): Сессия подключения к БД
        user_id (int): id пользователя

    Returns:
        list[dict]: Список личных пар слов пользователя
    """
    stmt = select(Translate).where(Translate.owner_user == user_id)
    pairs = session.execute(stmt).scalars().all()

    results = []
    for pair in pairs:
        results.append({
            'translate_id': pair.id,
            'word_en': pair.word_en.word,
            'word_ru': pair.word_ru.word,
            'transcription': pair.word_en.transcription
        })

    return results


def delete_user_word(session: Session, user_id: int, translate_id: int) -> bool:
    """Удаляет личное слово пользователя.

    Удаляет только если слово принадлежит пользователю (owner_user = user_id).

    Args:
        session (Session): Сессия подключения к БД
        user_id (int): id пользователя
        translate_id (int): id пары слов из Translate

    Returns:
        bool: True если удалено успешно, False при ошибке
    """
    from sql_db.models import UserTranslationProgress, UserAttempt

    stmt = select(Translate).where(
        and_(
            Translate.id == translate_id,
            Translate.owner_user == user_id
        )
    )
    pair = session.execute(stmt).scalar_one_or_none()

    if pair is None:
        print('Слово не найдено или не принадлежит пользователю')
        return False

    # Удаляем связанный прогресс
    session.query(UserTranslationProgress).filter(
        UserTranslationProgress.translate_id == translate_id
    ).delete()

    # Удаляем историю попыток
    session.query(UserAttempt).filter(
        UserAttempt.translate_id == translate_id
    ).delete()

    # Удаляем саму пару
    session.delete(pair)
    session.flush()
    print(f'Слово {translate_id} удалено')
    return True


def get_random_words(session: Session, user_id: int, limit: int = 20) -> list[dict]:
    """Получает случайные слова для обучения.

    Приоритет:
    1. Все личные слова пользователя (owner_user = user_id)
    2. Все избранные слова (UserFavorite)
    3. Рандом из главного словаря до заполнения лимита

    Args:
        session (Session): Сессия подключения к БД
        user_id (int): id пользователя
        limit (int): Максимальное количество слов

    Returns:
        list[dict]: Список пар слов для обучения
    """
    results = []
    used_ids = set()

    # 1. Личные слова пользователя
    user_words = get_user_words(session, user_id)
    for word in user_words:
        if len(results) >= limit:
            break
        results.append(word)
        used_ids.add(word['translate_id'])

    # 2. Избранные слова
    if len(results) < limit:
        favorites = get_user_favorites(session, user_id)
        for fav in favorites:
            if len(results) >= limit:
                break
            if fav['translate_id'] not in used_ids:
                results.append(fav)
                used_ids.add(fav['translate_id'])

    # 3. Рандом из главного словаря
    if len(results) < limit:
        remaining = limit - len(results)
        stmt = select(Translate).where(
            and_(
                Translate.owner_user.is_(None),
                ~Translate.id.in_(used_ids) if used_ids else True
            )
        ).order_by(func.random()).limit(remaining)

        random_pairs = session.execute(stmt).scalars().all()

        for pair in random_pairs:
            results.append({
                'translate_id': pair.id,
                'word_en': pair.word_en.word,
                'word_ru': pair.word_ru.word,
                'transcription': pair.word_en.transcription
            })

    return results


def is_word_in_favorites(session: Session, user_id: int, translate_id: int) -> bool:
    """Проверяет, находится ли слово в избранном пользователя.

    Args:
        session (Session): Сессия подключения к БД
        user_id (int): id пользователя
        translate_id (int): id пары слов

    Returns:
        bool: True если слово в избранном
    """
    stmt = select(UserFavorite).where(
        and_(
            UserFavorite.user_id == user_id,
            UserFavorite.translate_id == translate_id
        )
    )
    return session.execute(stmt).scalar_one_or_none() is not None


def remove_word_from_user_list(session: Session, user_id: int, translate_id: int) -> dict:
    """Удаляет слово из избранного/личного списка пользователя.

    Логика:
    1. Если слово личное (owner_user = user_id) → удаляем из Translate
    2. Если слово глобальное → удаляем из UserFavorite

    Args:
        session (Session): Сессия подключения к БД
        user_id (int): id пользователя
        translate_id (int): id пары слов

    Returns:
        dict: {'success': bool, 'message': str}
    """
    from sql_db.models import UserTranslationProgress, UserAttempt

    # Проверяем, существует ли пара
    translate = session.get(Translate, translate_id)
    if translate is None:
        return {'success': False, 'message': 'Слово не найдено'}

    # Если это личное слово пользователя — удаляем полностью
    if translate.owner_user == user_id:
        # Удаляем связанный прогресс
        session.query(UserTranslationProgress).filter(
            UserTranslationProgress.translate_id == translate_id
        ).delete()

        # Удаляем историю попыток
        session.query(UserAttempt).filter(
            UserAttempt.translate_id == translate_id
        ).delete()

        # Удаляем саму пару
        session.delete(translate)
        session.flush()
        return {'success': True, 'message': 'Слово удалено'}

    # Если это глобальное слово — удаляем из избранного
    fav_stmt = select(UserFavorite).where(
        and_(
            UserFavorite.user_id == user_id,
            UserFavorite.translate_id == translate_id
        )
    )
    favorite = session.execute(fav_stmt).scalar_one_or_none()

    if favorite is None:
        return {'success': False, 'message': 'Слово не в избранном'}

    session.delete(favorite)
    session.flush()
    return {'success': True, 'message': 'Слово удалено из избранного'}
