# SQL запросы для Telegram

from sqlalchemy import select
from sqlalchemy.orm import Session

from sql_db.models import User

def get_user(session: Session,
             user_nickname: str | None = None, 
             user_id: int | None = None) -> int | None:
    """Функция ищет потльзователя по id либо никнейму тг
    Используется для поиска перед записью нового пользователя и для поиска на нужды кода

    Args:
        session (Session): в основной коде используем with get_session() as и мерезаем сессию в вызываемую функцию
        user_nickname (str | None, optional): _Никнейм пользователя
        user_id (int | None, optional): id пользователя в базе.

    Returns:
        int | None : id пользователя
    """
    # Проверяем что хотябы одно поле для поиска заполнено
    if user_nickname is None and user_id is None:
        print('Все поля для поиска пустые, ничего не передано')
        return None

    print('Формируем запрос поиска в БД')
    
    stmt = select(User)

    # Формируем запрос для БД
    if user_id is not None:
        stmt = stmt.where(User.id == user_id)
    else:
        stmt = stmt.where(User.user_tg_nickname == user_nickname)

    # Делаем запрос в БД
    obj_user = session.execute(stmt).scalar_one_or_none()

    # Проверяем если не найдено
    if obj_user is not None:
        user_id_db = obj_user.id
        print(f'Найден пользователь {user_id_db}')
        return user_id_db

    # Если пользователь не найден
    print('Пользователь не найден')
    return None

def create_user(session: Session, user_nikname: str) -> int | None:
    """Функция сначала проверяет наличие пользователя в базе
    Если такого пользователя не сущетсвует, то добавляет пользователя в базу

    Args:
        session (Session): Сессия подключения к БД
        user_nikname (str): Телеграм никнейм пользователя

    Returns:
        int | None: Если пользователь jncencndetn в базе, то добавляем в БД и возвращаем id
        если пользователь уже существует, то возвращает None
    """
    # Проверяем что  user_nikname не пустой и что строка
    if user_nikname is None or not isinstance(user_nikname, str):
        print('Ошибка имени пользователя, введите корректные данные')
        return None
        
    # Проверяем естьли такой пользователь в БД
    db_user_id = get_user(session=session, user_nickname=user_nikname)
    # Если пользователь не найден, то добавим его в БД
    if db_user_id is None:
        new_user = User(user_tg_nickname = user_nikname)
        session.add(new_user)
        session.flush()
        db_user_id = new_user.id
        print(f'Пользователь добавлен в БД: {db_user_id}')
        return db_user_id

    # Если пользователь найден
    print(f'Пользователь с таким именем уже существует в базе {db_user_id}')
    return None


def get_or_create_user(session: Session, user_nickname: str) -> int | None:
    """Получает существующего пользователя или создает нового.

    Главная функция для работы с пользователями в боте.
    Если пользователь существует — возвращает его id.
    Если не существует — создает и возвращает id нового пользователя.

    Args:
        session (Session): Сессия подключения к БД
        user_nickname (str): Телеграм никнейм пользователя

    Returns:
        int | None: id пользователя или None при ошибке
    """
    if user_nickname is None or not isinstance(user_nickname, str):
        print('Ошибка: некорректный никнейм пользователя')
        return None

    # Пробуем найти существующего пользователя
    user_id = get_user(session=session, user_nickname=user_nickname)

    if user_id is not None:
        print(f'Пользователь найден: {user_id}')
        return user_id

    # Если не найден — создаем нового
    new_user = User(user_tg_nickname=user_nickname)
    session.add(new_user)
    session.flush()
    user_id = new_user.id
    print(f'Создан новый пользователь: {user_id}')
    return user_id


def delete_user(session: Session, user_id: int) -> bool:
    """Удаляет пользователя и все связанные с ним данные.

    Используется когда пользователь отключает бота.
    Каскадно удаляет: прогресс обучения, попытки, избранное, личные слова.

    Args:
        session (Session): Сессия подключения к БД
        user_id (int): id пользователя в базе

    Returns:
        bool: True если удаление успешно, False при ошибке
    """
    from sql_db.models import UserTranslationProgress, UserAttempt, UserFavorite, Translate

    # Проверяем существование пользователя
    user = session.get(User, user_id)
    if user is None:
        print(f'Пользователь {user_id} не найден')
        return False

    # Удаляем связанные данные
    # 1. Прогресс обучения
    session.query(UserTranslationProgress).filter(
        UserTranslationProgress.user_id == user_id
    ).delete()

    # 2. История попыток
    session.query(UserAttempt).filter(
        UserAttempt.user_id == user_id
    ).delete()

    # 3. Избранное
    session.query(UserFavorite).filter(
        UserFavorite.user_id == user_id
    ).delete()

    # 4. Личные слова пользователя (Translate с owner_user = user_id)
    session.query(Translate).filter(
        Translate.owner_user == user_id
    ).delete()

    # 5. Удаляем самого пользователя
    session.delete(user)
    session.flush()

    print(f'Пользователь {user_id} и все его данные удалены')
    return True