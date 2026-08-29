import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# 1. Получаем строку подключения из переменных окружения
raw_url = os.getenv('DATABASE_URL', 'sqlite:///./data/notes_app.db')

# 2. Безопасно вычисляем абсолютный путь к папке и файлу базы через Path
if raw_url.startswith('sqlite:///'):
    # Отрезаем sqlite:/// и вычисляем чистый абсолютный путь
    db_file_path = Path(raw_url.replace('sqlite:///', '')).resolve()
    # .as_posix() гарантирует правильный строковый формат пути без дублирования слэшей
    DATABASE_URL = f'sqlite:///{db_file_path.as_posix()}'
else:
    db_file_path = None
    DATABASE_URL = raw_url

# 3. Автоматически создаем папку для базы данных, если её нет
if db_file_path:
    db_dir = db_file_path.parent
    db_dir.mkdir(parents=True, exist_ok=True)

# 4. Инициализируем движок SQLAlchemy
engine = create_engine(
    DATABASE_URL, 
    connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}
)

# Оптимизации производительности SQLite для продакшена (Pragma-настройки)
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
