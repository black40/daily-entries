import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Имя файла базы данных
DATABASE_URL = "sqlite:///./notes_app.db"

# check_same_thread=False нужен только для SQLite, так как FastAPI асинхронный
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# Обязательные оптимизации для продакшена SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    # 1. Включаем WAL-режим (чтение не блокирует запись)
    cursor.execute("PRAGMA journal_mode=WAL")
    # 2. Оптимизируем синхронизацию с диском для скорости
    cursor.execute("PRAGMA synchronous=NORMAL")
    # 3. Включаем поддержку внешних ключей (Foreign Keys)
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Настройка сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для ваших будущих моделей (таблиц Заметок, Желаний и т.д.)
class Base(DeclarativeBase):
    pass

# Зависимость (Dependency) для роутов FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
