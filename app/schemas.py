from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class NoteCreateSchema(BaseModel):
    """Схема для формы добавления новой заметки."""
    title: str = Field(title="Заголовок заметки", max_length=100)
    content: str = Field(title="Текст заметки")

class NoteReadSchema(BaseModel):
    """Схема для отображения в таблице FastUI."""
    id: int
    title: str
    created_at: datetime

    # Правильная конфигурация для Pydantic v2
    model_config = ConfigDict(from_attributes=True)

class NoteReadSchema(BaseModel):
    """Схема для отображения в таблице FastUI и детального просмотра."""
    id: int
    title: str
    content: str  # <-- ДОБАВИЛИ ЭТО ПОЛЕ
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
