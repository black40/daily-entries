from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Note(Base):
    """Модель для ежедневных записок и дневника."""
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), index=True)  # Заголовок заметки
    content: Mapped[str] = mapped_column(Text)                    # Текст заметки
    
    # Автоматически ставит текущее время при создании
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    # Время обновления (меняется при редактировании)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )


class WishItem(Base):
    """Модель для списка желаний (Wishlist)."""
    __tablename__ = "wish_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(150))               # Что хочется купить/получить
    description: Mapped[Optional[str]] = mapped_column(Text)     # Описание, ссылка, мысли
    price: Mapped[Optional[float]] = mapped_column(insert_default=None) # Ориентировочная цена
    
    # Статус: куплено / подарено / еще актуально
    is_granted: Mapped[bool] = mapped_column(default=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
