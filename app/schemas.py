from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class NoteCreateSchema(BaseModel):
    """Схема для формы добавления новой заметки."""
    title: str = Field(title="Заголовок заметки", max_length=100)
    content: str = Field(title="Текст заметки")

class NoteReadSchema(BaseModel):
    """Схема для отображения в таблице FastUI и детального просмотра."""
    id: int
    title: str
    content: str
    created_at: datetime
    
    # Виртуальное поле для интерактивного действия в строке таблицы
    archive_action: str = ""

    model_config = ConfigDict(from_attributes=True)
