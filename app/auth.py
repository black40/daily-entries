import bcrypt

def hash_password(password: str) -> str:
    '''Превращает чистый текстовый пароль в безопасный хэш для базы данных.'''
    # Превращаем строку в байты
    password_bytes = password.encode('utf-8')
    # Генерируем случайную соль и вычисляем хэш
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    # Переводим результат обратно в строку для хранения в SQLite
    return hashed_bytes.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    '''Проверяет, совпадает ли введенный пароль с хэшем из базы данных.'''
    plain_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    # Сравниваем введенный пароль с сохраненным хэшем
    return bcrypt.checkpw(plain_bytes, hashed_bytes)
