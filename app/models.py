from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, ForeignKey, DateTime, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    '''Модель пользователя для регистрации и авторизации.'''
    __tablename__ = 'users'

    model_config = {'from_attributes': True}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )

    # Связь «Один ко многим»: у одного пользователя может быть много заметок
    notes: Mapped[List['Note']] = relationship(back_populates='user', cascade='all, delete-orphan')


class Note(Base):
    '''Модель для ежедневных записок и дневника с привязкой к пользователю.'''
    __tablename__ = 'notes'

    model_config = {'from_attributes': True}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), index=True)
    content: Mapped[str] = mapped_column(Text)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # ВНЕШНИЙ КЛЮЧ: привязываем заметку к конкретному пользователю
        # ИСПРАВЛЕНО: Добавлен index=True для быстрого поиска заметок по пользователю
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )

    # Обратная связь для SQLAlchemy
    user: Mapped['User'] = relationship(back_populates='notes')


class WishItem(Base):
    '''Модель для списка желаний (Wishlist) — пока ждет своего часа.'''
    __tablename__ = 'wish_items'

    model_config = {'from_attributes': True}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[Optional[str]] = mapped_column(Text)
    price: Mapped[Optional[float]] = mapped_column(insert_default=None)
    is_granted: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
