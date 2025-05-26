from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from typing import Optional, List, Dict, Any
from loguru import logger
import os
import traceback
import json

Base = declarative_base()

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, unique=True)
    chat_id = Column(Integer)
    user_id = Column(Integer)
    text = Column(String)
    date = Column(DateTime)
    is_processed = Column(Boolean, default=False)
    wiki_page = Column(String, nullable=True)
    analysis = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MediaFile(Base):
    __tablename__ = 'media_files'

    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey('messages.id'))
    file_id = Column(String)
    file_name = Column(String)
    file_type = Column(String)
    wiki_file_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    message = relationship("Message", back_populates="media_files")

Message.media_files = relationship("MediaFile", back_populates="message")

class Database:
    def __init__(self, db_path: str = "data/bot.db"):
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self.db_path = db_path

    async def setup(self) -> bool:
        """Инициализация базы данных"""
        try:
            logger.info("Начало инициализации базы данных...")
            
            # Создаем директорию для базы данных, если её нет
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Создаем таблицы
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("База данных успешно инициализирована")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {str(e)}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            logger.error(f"Трассировка:\n{traceback.format_exc()}")
            return False

    async def add_message(self, message_id: int, chat_id: int, user_id: int, text: str, date: datetime, analysis: Optional[Dict[str, Any]] = None) -> Optional[Message]:
        """Добавление нового сообщения"""
        try:
            async with self.async_session() as session:
                # Проверяем, существует ли сообщение
                result = await session.execute(
                    select(Message).filter_by(message_id=message_id)
                )
                existing_message = result.scalar_one_or_none()
                
                if existing_message:
                    logger.info(f"Сообщение {message_id} уже существует в базе данных")
                    return existing_message
                
                message = Message(
                    message_id=message_id,
                    chat_id=chat_id,
                    user_id=user_id,
                    text=text,
                    date=date,
                    analysis=json.dumps(analysis) if analysis else None
                )
                session.add(message)
                await session.commit()
                return message
        except Exception as e:
            logger.error(f"Ошибка при добавлении сообщения: {e}")
            return None

    async def add_media_file(self, message_id: int, file_id: str, file_name: str, file_type: str) -> Optional[MediaFile]:
        """Добавление нового медиафайла"""
        try:
            async with self.async_session() as session:
                media_file = MediaFile(
                    message_id=message_id,
                    file_id=file_id,
                    file_name=file_name,
                    file_type=file_type
                )
                session.add(media_file)
                await session.commit()
                return media_file
        except Exception as e:
            logger.error(f"Ошибка при добавлении медиафайла: {e}")
            return None

    async def get_unprocessed_messages(self) -> List[Message]:
        """Получение необработанных сообщений"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(Message).filter_by(is_processed=False)
                )
                return result.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка при получении необработанных сообщений: {e}")
            return []

    async def mark_message_as_processed(self, message_id: int, wiki_page: str) -> bool:
        """Отметка сообщения как обработанного"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(Message).filter_by(message_id=message_id)
                )
                message = result.scalar_one_or_none()
                if message:
                    message.is_processed = True
                    message.wiki_page = wiki_page
                    await session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Ошибка при отметке сообщения как обработанного: {e}")
            return False

    async def get_processed_messages(self) -> list[int]:
        """Получение списка ID обработанных сообщений"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(Message.message_id)
                    .where(Message.is_processed == True)
                )
                return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Ошибка при получении списка обработанных сообщений: {str(e)}")
            return []

    async def close(self):
        """Закрытие соединения с базой данных"""
        await self.engine.dispose() 