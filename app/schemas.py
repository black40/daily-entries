from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class NoteCreateSchema(BaseModel):
    """Схема для формы добавления новой заметки."""
    title: str = Field(title="Заголовок заметки", max_length=100)
    content: str = Field(title="Текст заметки")

class NoteReadSchema(BaseModel):
    """Схема для отображения заметок в таблице FastUI."""
    id: int
    title: str
    content: str
    created_at: datetime
    
    # Легальные текстовые поля, которые таблица превратит в кликабельные кнопки
    archive_action: str = "📦 В архив"
    unarchive_action: str = "↩️ Вернуть"
    delete_action: str = "❌ Удалить"

    model_config = ConfigDict(from_attributes=True)
