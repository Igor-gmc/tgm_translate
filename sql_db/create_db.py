# Файл просто вормируем словарный запас в SQL

from sqlalchemy import select, and_

from sql_db.db_init import get_session, engine
from sql_db.models import Base, WordEn, WordRu, Translate

import csv
from typing import Type, Optional, Union

def check_and_write_word(session, 
                         WordClass: Type, 
                         word_in: str, 
                         transcription: Optional[str] = None
                         ) -> Union[int, None]:
    """Функция получает данные для поиска дубликатов с таблице
    если слово в словаре не найдено, то слово записывается в словарь
    
    В функцию передаем:
        session - сессию подключения к БД
        WordClass - класс, который определяет в какую таблицу будет записано слово
        word_in: str - передем само слово en | ru
        transcription: str|None - если есть транскрибация, то передаем

    Returns:
        int | None: возвращается id слова из таблицы БД или None если слово добавить не удалось
    """
    # Ищем его в таблице, если слова нет, то вернется None
    obj_word = session.execute(
        select(WordClass).where(WordClass.word == word_in)
    ).scalar_one_or_none()

    # Пробуем вернуть id слова, если оно найдено
    if obj_word:
        return obj_word.id

    # Если слово не найдено, то создаем объект
    data = {"word": word_in}
    if hasattr(WordClass, 'transcription') and transcription is not None:
        data['transcription'] = transcription

    obj_word = WordClass(**data)
    session.add(obj_word)
    session.flush() # получаем объект id

    return obj_word.id # Получаем и возвращаем id слова

def create_init_data():
    try:
        print('Создаем таблицы базы данных')
        Base.metadata.create_all(bind=engine)

        # открываем сессию
        with get_session() as session:
            # читаем по строкам csv файл
            with open('data_words/mueller_dictionary.csv', 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # пропускаем заголовок CSV

                # Читаем файл по строкам чтобы экономить память
                for i, line in enumerate(reader, start=1):
                    # Берем каждую 100-ю строку, чтобы не перегружать словарь
                    if i % 100 == 0:
                        # ['id_015236', 'believer', "[bI'li:vэ]", 'защитник'] - это структура строки
                        
                        # Записываем en слово + transcription
                        en_word_text = line[1].strip()
                        en_transcription_text = line[2].strip()
                        id_en_word = check_and_write_word(session=session,
                                                          WordClass=WordEn,
                                                          word_in=en_word_text,
                                                          transcription=en_transcription_text)
                        # Записываем ru слово
                        ru_word_text = line[3].strip()
                        id_ru_word = check_and_write_word(session=session,
                                                          WordClass=WordRu,
                                                          word_in=ru_word_text)

                        # записываем в Translate связку id word_en, id word_ru
                        # и создателя записи owner_user = NULL
                        if id_en_word is not None and id_ru_word is not None:
                            # Ищем совпадение пары, если такое совпадение есть, то пропускаем запись
                            obj_translate = session.execute(select(Translate).where(
                                    and_(
                                        (Translate.word_e == id_en_word),
                                        (Translate.word_r == id_ru_word)
                                    )
                                )
                            ).scalar_one_or_none()

                            if obj_translate is None:
                                # Записываем слова в таблицу перевода
                                # слова будут доступны всем, так как при записи владелец по умолчанию будет None
                                data = {'word_e': id_en_word, 'word_r': id_ru_word}
                                obj_translate = Translate(**data)
                                session.add(obj_translate)
                                session.flush() # получаем объект id
                                id_translate = obj_translate.id # Получаем id пары перевода
                            else:
                                id_translate = obj_translate.id

                            print(f'Записана пара {id_translate} в таблицу переводов')
                            print(f'Слово {id_en_word}:{en_word_text}, перевод: {id_ru_word}:{ru_word_text}')

    except Exception as e:
        print(f'Импорт не удался, ошибка: {e}')

if __name__ == '__main__':
    create_init_data()
