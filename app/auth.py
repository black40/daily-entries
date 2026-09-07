import os
import bcrypt
from typing import Optional
from fastapi import Request, Depends
from sqlalchemy.orm import Session
from itsdangerous import Signer, BadSignature

# Импортируем наши модели и сессию базы данных
from app import models
from app.database import get_db

# Секретный ключ для подписи сессий
SECRET_KEY = os.getenv('DIARY_SECRET_KEY', 'fallback-secret-key-for-dev')

def hash_password(password: str) -> str:
    '''Превращает чистый текстовый пароль в безопасный хэш для базы данных через bcrypt.'''
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    '''Проверяет, совпадает ли введенный пароль с хэшем из базы данных через bcrypt.'''
    plain_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[models.User]:
    '''
    Зависимость для FastAPI. 
    Извлекает пользователя из куки-сессии, проверяет его наличие в БД.
    Если кука протухла, битая или пользователя удалили из SQLite — возвращает None.
    '''
    cookie_value = request.cookies.get('diary_session')
    if not cookie_value:
        return None

    try:
        # Проверяем криптографическую подпись куки
        signer = Signer(SECRET_KEY)
        user_id_str = signer.unsign(cookie_value).decode('utf-8')
        user_id = int(user_id_str)
        
        # Жесткая проверка: ищем пользователя в базе данных физически!
        user = db.query(models.User).filter(models.User.id == user_id).first()
        return user  # Возвращает живой объект пользователя или None
        
    except (BadSignature, ValueError):
        return None
