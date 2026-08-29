from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, SecretStr

class NoteCreateSchema(BaseModel):
    '''Схема для формы добавления новой заметки.'''
    title: str = Field(title='Заголовок заметки', max_length=100)
    content: str = Field(title='Текст заметки')
    category_id: Optional[int] = Field(default=None, title='Категория')

class NoteReadSchema(BaseModel):
    '''Схема для отображения заметок в таблице FastUI.'''
    id: int
    title: str
    content: str
    created_at: datetime
    category_id: Optional[int] = None
    archive_action: str = ''
    delete_action: str = '❌ Удалить'

    model_config = ConfigDict(from_attributes=True)

class UserRegisterSchema(BaseModel):
    '''Форма регистрации нового пользователя.'''
    email: str = Field(title='Электронная почта', max_length=150)
    password: SecretStr = Field(title='Пароль', max_length=50)

class UserLoginSchema(BaseModel):
    '''Форма входа в приложение.'''
    email: str = Field(title='Электронная почта')
    password: SecretStr = Field(title='Пароль')

class UserReadSchema(BaseModel):
    '''Схема для вывода списка пользователей в админской таблице.'''
    id: int
    email: str
    created_at: datetime
    delete_action: str = '❌ Удалить'

    model_config = ConfigDict(from_attributes=True)

# НОВАЯ СХЕМА ДЛЯ КАТЕГОРИЙ
class CategoryCreateSchema(BaseModel):
    '''Схема для создания новой категории.'''
    name: str = Field(title='Название категории', max_length=50)

class CategoryReadSchema(BaseModel):
    '''Схема для чтения категорий.'''
    id: int
    name: str
    user_id: int

    model_config = ConfigDict(from_attributes=True)
