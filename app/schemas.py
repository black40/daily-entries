from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

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
    
    # Дефолтные значения для интерактивных колонок действий
    archive_action: str = ''
    delete_action: str = '❌ Удалить'  # <-- ВОТ ЭТО ПОЛЕ ОЖИВИТ КНОПКУ

    model_config = ConfigDict(from_attributes=True)


# Заготовки для будущей регистрации
class UserRegisterSchema(BaseModel):
    '''Форма регистрации нового пользователя.'''
    email: str = Field(title='Электронная почта', max_length=150)
    password: str = Field(title='Пароль', max_length=50)

class UserLoginSchema(BaseModel):
    '''Форма входа в приложение.'''
    email: str = Field(title='Электронная почта')
    password: str = Field(title='Пароль')
