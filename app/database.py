import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# 1. Получаем строку подключения из переменных окружения (для продакшена)
raw_url = os.getenv('DATABASE_URL', 'sqlite:///./data/notes_app.db')

# 2. ИСПРАВЛЕНО: Безопасно вычисляем абсолютный путь к папке и файлу базы через Path
if raw_url.startswith('sqlite:///'):
    # Отрезаем sqlite:/// и превращаем остаток в полноценный объект пути Path
    # .resolve() превратит относительный путь './data/...' в железный абсолютный адрес
    db_file_path = Path(raw_url.replace('sqlite:///', '')).resolve()
    # Собираем эталонную строку подключения для движка
    DATABASE_URL = f'sqlite:///{db_file_path}'
else:
    db_file_path = None
    DATABASE_URL = raw_url

# 3. Автоматически создаем папку со всеми родительскими директориями, если её нет
if db_file_path:
    db_dir = db_file_path.parent
    db_dir.mkdir(parents=True, exist_ok=True)

# 4. Инициализируем движок SQLAlchemy (используем проверенную строку подключения)
engine = create_engine(
    DATABASE_URL, 
    connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}
)

# Оптимизации производительности SQLite для продакшена (Ваши Pragma-настройки в полной сохранности!)
@event.listens_for(engine, 'connect')
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute('PRAGMA journal_mode=WAL')
    cursor.execute('PRAGMA synchronous=NORMAL')
    cursor.execute('PRAGMA foreign_keys=ON')
    cursor.close()

# Настройка фабрики сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
