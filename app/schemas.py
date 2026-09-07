from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict, SecretStr


class NoteCreateSchema(BaseModel):
    '''Схема для создания заметки через ModelForm/c.Form.'''
    title: str = Field(title='Название заметки')
    content: str = Field(title='Текст заметки (поддерживает Markdown)')
    # ИСПРАВЛЕНО: Разрешаем на уровне типов принимать И число, И строку, И None
    category_id: Optional[int | str] = Field(None, title='ID Категории')

    @field_validator('category_id', mode='before')
    @classmethod
    def empty_string_to_none(cls, value):
        # Если значение пустое во всех проявлениях — жестко возвращаем None
        if value is None or str(value).strip() in ('', '0', 'None', 'null'):
            return None
        # Во всех остальных случаях принудительно отдаем чистый int для SQLite!
        try:
            return int(value)
        except ValueError:
            return None


class NoteReadSchema(BaseModel):
    '''Схема для отображения заметок в таблице FastUI.'''
    id: int
    title: str
    content: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    user_id: int
    category_id: Optional[int] = None
    
    # Виртуальные поля для интерфейса FastUI
    category_name: Optional[str] = None
    archive_action: Optional[str] = None
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
    
    delete_action: str = '❌ Удалить'
    model_config = ConfigDict(from_attributes=True)
