import os
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import URL

from contextlib import contextmanager

def main():
    load_dotenv()

    # создаем ссылку на БД SQL
    DSN = URL.create(
        drivername='postgresql+psycopg2',
        username=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        host=os.getenv('POSTGRES_HOST'),
        port=os.getenv('POSTGRES_PORT'),
        database=os.getenv('POSTGRES_DB')
    )

    # создаем очередь подключений
    engine = create_engine(DSN, echo=True)
    LocalSession = sessionmaker(engine)

    # инициализируем доступ с закрытием сессии
    @contextmanager
    def get_session():
        session = LocalSession()
        try:
            # генерируем сессию и коммитим после выполнения
            yield session
            session.commit()
        except:
            # в сдучае ошибки откатываем операцию
            session.rollback()
            raise
        finally:
            # закрываем сесисю
            session.close()

if __name__ == '__main__':
    main()