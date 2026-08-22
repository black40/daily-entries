from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, SecretStr  # <-- Добавили SecretStr

class NoteCreateSchema(BaseModel):
    '''Схема для формы добавления новой заметки.'''
    title: str = Field(title='Заголовок заметки', max_length=100)
    content: str = Field(title='Текст заметки')

class NoteReadSchema(BaseModel):
    '''Схема для отображения в таблице FastUI.'''
    id: int
    title: str
    content: str
    created_at: datetime
    archive_action: str = ''
    delete_action: str = '❌ Удалить'

    model_config = ConfigDict(from_attributes=True)

class UserRegisterSchema(BaseModel):
    '''Форма регистрации нового пользователя с маскировкой пароля.'''
    email: str = Field(title='Электронная почта', max_length=150)
    # Заменили str на SecretStr, чтобы скрыть пароль в браузере
    password: SecretStr = Field(title='Пароль', max_length=50)

class UserLoginSchema(BaseModel):
    '''Форма входа в приложение.'''
    email: str = Field(title='Электронная почта')
    password: SecretStr = Field(title='Пароль')
