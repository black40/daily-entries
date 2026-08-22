from typing import Optional
from fastapi import Request, Response
from itsdangerous import Signer, BadSignature

# ... весь остальной код в session.py ниже оставляем прежним


# Секретный ключ для подписи Cookie (в реальном проекте берется из ENV)
SECRET_KEY = 'super-secret-diary-key-123'
signer = Signer(SECRET_KEY)

def set_user_session(response: Response, user_id: int):
    '''Кодирует ID пользователя и сохраняет в защищенную Cookie.'''
    signed_id = signer.sign(str(user_id).encode('utf-8'))
    response.set_cookie(
        key='diary_session',
        value=signed_id.decode('utf-8'),
        httponly=True,  # Защита от кражи через JavaScript-скрипты
        max_age=3600 * 24 * 7  # Сессия живет 7 дней
    )

def get_user_from_session(request: Request) -> Optional[int]:
    '''Читает Cookie, проверяет цифровую подпись и возвращает ID пользователя.'''
    session_value = request.cookies.get('diary_session')
    if not session_value:
        return None
    try:
        unsigned_id = signer.unsign(session_value.encode('utf-8'))
        return int(unsigned_id.decode('utf-8'))
    except (BadSignature, ValueError):
        return None
