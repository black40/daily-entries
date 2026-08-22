from typing import Optional
from fastapi import Request, Response
from itsdangerous import Signer, BadSignature

SECRET_KEY = 'super-secret-diary-key-123'
signer = Signer(SECRET_KEY)
COOKIE_MAX_AGE = 3600 * 24 * 7  # 7 дней в секундах


def set_user_session(response: Response, user_id: int):
    '''Кодирует ID пользователя и сохраняет в защищенную Cookie.'''
    signed_id = signer.sign(str(user_id).encode('utf-8'))
    response.set_cookie(
        key='diary_session',
        value=signed_id.decode('utf-8'),
        httponly=True,
        max_age=COOKIE_MAX_AGE
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


def refresh_user_session(request: Request, response: Response):
    '''Продлевает сессию еще на 7 дней при каждом активном действии.'''
    session_value = request.cookies.get('diary_session')
    if session_value:
        try:
            # Проверяем, что подпись не сломана
            signer.unsign(session_value.encode('utf-8'))
            # Перезаписываем ту же самую куку, сдвигая срок годности max_age
            response.set_cookie(
                key='diary_session',
                value=session_value,
                httponly=True,
                max_age=COOKIE_MAX_AGE
            )
        except BadSignature:
            pass
