import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# 1. Получаем строку подключения из переменных окружения (для продакшена)
#    Если её нет, используем локальный дефолт с папкой 'data' в корне
raw_url = os.getenv("DATABASE_URL", "sqlite:///./data/notes_app.db")

# 2. Переводим путь к файлу БД в объект Path для безопасной работы
#    Удаляем префикс 'sqlite:///' для вычисления системного пути
db_file_path = Path(raw_url.replace("sqlite:///", ""))

# 3. Вычисляем родительскую папку (например, ./data)
db_dir = db_file_path.parent

# 4. Автоматически создаем папку со всеми родительскими директориями, если её нет.
#    exist_ok=True предотвращает ошибку, если папка уже существует.
db_dir.mkdir(parents=True, exist_ok=True)

# 5. Инициализируем движок SQLAlchemy
engine = create_engine(
    raw_url, 
    connect_args={"check_same_thread": False}
)

# Оптимизации производительности SQLite для продакшена
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
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
