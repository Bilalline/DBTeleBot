import asyncio
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import PeerChannel

from database import Database
from wiki_client import WikiClient
from ollama_client import OllamaClient

# Настройка логирования
logger.add("logs/bot.log", rotation="1 day", retention="7 days", level="INFO")

# Загрузка переменных окружения
load_dotenv()

def get_env_int(key: str, default: Optional[int] = None) -> Optional[int]:
    """Безопасное получение целочисленного значения из переменных окружения"""
    value = os.getenv(key)
    if not value or value.startswith('your_'):
        logger.warning(f"Переменная окружения {key} не установлена или содержит placeholder значение")
        return default
    try:
        return int(value)
    except ValueError:
        logger.error(f"Невозможно преобразовать значение {value} для {key} в число")
        return default

class TelegramUserClient:
    def __init__(self):
        self.api_id = int(os.getenv('TELEGRAM_API_ID'))
        self.api_hash = os.getenv('TELEGRAM_API_HASH')
        self.phone = os.getenv('TELEGRAM_PHONE')
        self.admin_id = int(os.getenv('ADMIN_ID'))
        self.group_id = int(os.getenv('GROUP_ID'))
        self.client = None
        self.bot = None
        self.db = None
        self.wiki_client = None
        self.ollama_client = None
        self.logger = logger

    async def setup(self):
        """Настройка клиента"""
        self.logger.info("=== Начало инициализации клиента ===")
        
        # Шаг 1: Инициализация базы данных
        self.logger.info("Шаг 1: Инициализация базы данных...")
        self.db = Database()
        await self.db.setup()
        self.logger.info("✓ База данных успешно инициализирована")
        
        # Шаг 2: Загрузка конфигурации
        self.logger.info("Шаг 2: Загрузка конфигурации...")
        self.logger.info(f"TELEGRAM_API_ID: {self.api_id}")
        self.logger.info("TELEGRAM_API_HASH: ✓")
        self.logger.info("TELEGRAM_PHONE: ✓")
        self.logger.info(f"ADMIN_ID: {self.admin_id}")
        self.logger.info(f"GROUP_ID: {self.group_id}")
        self.logger.info("WIKI_USERNAME: ✓")
        self.logger.info("WIKI_PASSWORD: ✓")
        self.logger.info("WIKI_SITE: ✓")
        self.logger.info("OLLAMA_URL: ✓")
        self.logger.info("OLLAMA_MODEL: ✓")
        
        # Шаг 3: Проверка обязательных переменных
        self.logger.info("Шаг 3: Проверка обязательных переменных...")
        if not all([self.api_id, self.api_hash, self.phone, self.admin_id, self.group_id]):
            raise ValueError("Не все обязательные переменные установлены")
        self.logger.info("✓ Все обязательные переменные установлены")
        
        # Шаг 4: Инициализация клиента Telegram
        self.logger.info("Шаг 4: Инициализация клиента Telegram...")
        
        # Проверяем наличие файла сессии
        session_path = Path("session/session.session")
        if not session_path.exists():
            self.logger.error("Файл сессии не найден")
            raise ValueError("Файл сессии не найден")
        
        try:
            # Читаем строку сессии из файла
            session_string = session_path.read_text().strip()
            if not session_string:
                self.logger.error("Файл сессии пуст")
                raise ValueError("Файл сессии пуст")
            
            self.client = TelegramClient(
                StringSession(session_string),
                self.api_id,
                self.api_hash
            )
            
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                self.logger.error("Сессия недействительна")
                raise ValueError("Сессия недействительна")
            
            me = await self.client.get_me()
            self.logger.info(f"✓ Авторизован как {me.first_name} (@{me.username})")
            
            # Проверка подключения к группе
            try:
                group = await self.client.get_entity(PeerChannel(self.group_id))
                self.logger.info(f"✓ Успешно подключен к супергруппе: {group.title} (ID: {group.id})")
            except Exception as e:
                self.logger.error(f"Ошибка при подключении к группе: {str(e)}")
                raise
            
            self.logger.info("✓ Клиент Telegram успешно инициализирован")
            
        except Exception as e:
            self.logger.error(f"Ошибка при инициализации клиента Telegram: {str(e)}")
            raise
        
        # Шаг 5: Инициализация клиента MediaWiki
        self.logger.info("Шаг 5: Инициализация клиента MediaWiki...")
        self.wiki_client = WikiClient()
        await self.wiki_client.setup(
            username=os.getenv('WIKI_USERNAME'),
            password=os.getenv('WIKI_PASSWORD'),
            wiki_url=os.getenv('WIKI_SITE')
        )
        self.logger.info("✓ Клиент MediaWiki успешно инициализирован")
        
        # Шаг 6: Инициализация клиента Ollama
        self.logger.info("Шаг 6: Инициализация клиента Ollama...")
        self.ollama_client = OllamaClient(
            url=os.getenv('OLLAMA_URL'),
            model=os.getenv('OLLAMA_MODEL')
        )
        await self.ollama_client.setup()
        self.logger.info("✓ Клиент Ollama успешно инициализирован")
        
        # Шаг 7: Настройка обработчиков сообщений
        self.logger.info("Шаг 7: Настройка обработчиков сообщений...")
        await self.setup_handlers()
        self.logger.info("✓ Обработчики сообщений успешно настроены")
        
        self.logger.info("=== Инициализация клиента успешно завершена ===")
        
        # Обработка истории сообщений
        self.logger.info("Начало обработки истории сообщений...")
        try:
            # Получаем сообщения порциями
            self.logger.info("Получение сообщений порциями...")
            offset_id = 0
            limit = 100
            total_processed = 0
            total_skipped = 0
            
            while True:
                try:
                    self.logger.info(f"Получение сообщений (offset_id={offset_id}, limit={limit})...")
                    messages = await self.client.get_messages(
                        PeerChannel(self.group_id),
                        limit=limit,
                        offset_id=offset_id
                    )
                    
                    if not messages:
                        self.logger.info("Больше сообщений нет")
                        break
                        
                    self.logger.info(f"Получено {len(messages)} сообщений")
                    
                    # Получаем список обработанных сообщений
                    processed_messages = await self.db.get_processed_messages()
                    self.logger.info(f"В базе данных найдено {len(processed_messages)} обработанных сообщений")
                    
                    for message in messages:
                        try:
                            if not message or not message.text:
                                self.logger.warning(f"Пропуск пустого сообщения {message.id if message else 'unknown'}")
                                continue
                                
                            if message.id not in processed_messages:
                                self.logger.info(f"Обработка исторического сообщения {message.id}...")
                                try:
                                    self.logger.info(f"Отправка сообщения {message.id} на анализ в Ollama...")
                                    analysis = await self.ollama_client.analyze_text(message.text)
                                    if analysis:
                                        self.logger.info(f"Получен анализ от Ollama для сообщения {message.id}: {analysis}")
                                        
                                        # Создание или обновление страницы в MediaWiki
                                        title = analysis.get('title', f"Сообщение_{message.id}")
                                        content = f"## {title}\n\n{message.text}\n\n"
                                        content += "### Метаданные\n"
                                        content += f"- Дата: {message.date}\n"
                                        content += f"- Автор: {message.sender_id}\n"
                                        content += f"- ID сообщения: {message.id}\n"

                                        self.logger.info(f"Подготовка данных для MediaWiki:")
                                        self.logger.info(f"Заголовок страницы: {title}")
                                        self.logger.info(f"Содержимое страницы:\n{content}")

                                        self.logger.info(f"Создание/обновление страницы в MediaWiki для сообщения {message.id}...")
                                        if await self.wiki_client.edit_page(title, content):
                                            await self.db.mark_message_as_processed(message.id, title)
                                            self.logger.info(f"✓ Сообщение {message.id} успешно обработано и сохранено в Wiki")
                                            total_processed += 1
                                        else:
                                            self.logger.error(f"Не удалось создать/обновить страницу в Wiki для сообщения {message.id}")
                                        
                                        await self.db.add_message(
                                            message_id=message.id,
                                            chat_id=message.chat_id,
                                            user_id=message.sender_id,
                                            text=message.text,
                                            date=message.date,
                                            analysis=analysis
                                        )
                                        self.logger.info(f"✓ Сообщение {message.id} успешно обработано")
                                    else:
                                        self.logger.error(f"Не удалось проанализировать историческое сообщение {message.id}")
                                except Exception as e:
                                    self.logger.error(f"Не удалось проанализировать историческое сообщение {message.id}")
                                    self.logger.error(f"Ошибка: {str(e)}")
                                    self.logger.error(f"Трассировка:\n{traceback.format_exc()}")
                            else:
                                total_skipped += 1
                                self.logger.info(f"Сообщение {message.id} уже обработано, пропускаем")
                        except Exception as e:
                            self.logger.error(f"Ошибка при обработке сообщения: {str(e)}")
                            self.logger.error(f"Трассировка:\n{traceback.format_exc()}")
                            continue
                    
                    # Обновляем offset_id для следующей порции
                    offset_id = messages[-1].id
                    self.logger.info(f"Обработано порции сообщений. Итоги:")
                    self.logger.info(f"- Обработано в этой сессии: {total_processed}")
                    self.logger.info(f"- Пропущено в этой сессии: {total_skipped}")
                    
                except Exception as e:
                    self.logger.error(f"Ошибка при получении порции сообщений: {str(e)}")
                    self.logger.error(f"Трассировка:\n{traceback.format_exc()}")
                    break
            
            self.logger.info(f"Итоги обработки:")
            self.logger.info(f"- Всего обработано: {total_processed}")
            self.logger.info(f"- Всего пропущено: {total_skipped}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке истории сообщений: {str(e)}")
            self.logger.error(f"Тип ошибки: {type(e).__name__}")
            self.logger.error(f"Трассировка:\n{traceback.format_exc()}")

    async def setup_handlers(self):
        """Настройка обработчиков сообщений"""
        @self.client.on(events.NewMessage(chats=PeerChannel(self.group_id)))
        async def handle_message(event):
            """Обработчик новых сообщений"""
            try:
                self.logger.info(f"Получено новое сообщение: ID={event.message.id}, Chat={event.chat_id}, User={event.sender_id}")
                self.logger.info(f"Текст сообщения: {event.message.text}")
                
                # Проверяем, что сообщение не от бота
                if event.message.out:
                    self.logger.info("Сообщение от бота, игнорируем")
                    return
                
                # Сохранение сообщения в базу данных
                self.logger.info(f"Сохранение сообщения {event.message.id} в базу данных...")
                message = await self.db.add_message(
                    message_id=event.message.id,
                    chat_id=event.chat_id,
                    user_id=event.sender_id,
                    text=event.message.text,
                    date=event.message.date
                )

                if not message:
                    self.logger.error(f"Не удалось сохранить сообщение {event.message.id}")
                    return
                self.logger.info(f"Сообщение {event.message.id} успешно сохранено в БД")

                # Анализ текста с помощью Ollama
                self.logger.info(f"Отправка сообщения {event.message.id} на анализ в Ollama...")
                analysis = await self.ollama_client.analyze_text(event.message.text)
                if not analysis:
                    self.logger.error(f"Не удалось проанализировать сообщение {event.message.id}")
                    return
                self.logger.info(f"Получен анализ от Ollama для сообщения {event.message.id}: {analysis}")

                # Создание или обновление страницы в MediaWiki
                title = analysis.get('title', f"Сообщение_{event.message.id}")
                content = f"## {title}\n\n{event.message.text}\n\n"
                content += "### Метаданные\n"
                content += f"- Дата: {event.message.date}\n"
                content += f"- Автор: {event.sender_id}\n"
                content += f"- ID сообщения: {event.message.id}\n"

                self.logger.info(f"Подготовка данных для MediaWiki:")
                self.logger.info(f"Заголовок страницы: {title}")
                self.logger.info(f"Содержимое страницы:\n{content}")

                self.logger.info(f"Создание/обновление страницы в MediaWiki для сообщения {event.message.id}...")
                if await self.wiki_client.edit_page(title, content):
                    await self.db.mark_message_as_processed(event.message.id, title)
                    self.logger.info(f"Сообщение {event.message.id} успешно обработано и сохранено в Wiki")
                else:
                    self.logger.error(f"Не удалось создать/обновить страницу в Wiki для сообщения {event.message.id}")

            except Exception as e:
                self.logger.error(f"Ошибка при обработке сообщения: {str(e)}")
                self.logger.error(f"Тип ошибки: {type(e).__name__}")
                self.logger.error(f"Трассировка:\n{traceback.format_exc()}")

        # Добавляем обработчик для всех сообщений в группе
        @self.client.on(events.NewMessage(chats=PeerChannel(self.group_id)))
        async def log_all_messages(event):
            """Логирование всех сообщений"""
            try:
                self.logger.info(f"Новое сообщение в группе: ID={event.message.id}, Chat={event.chat_id}, User={event.sender_id}")
                self.logger.info(f"Текст: {event.message.text}")
            except Exception as e:
                self.logger.error(f"Ошибка при логировании сообщения: {str(e)}")

        self.logger.info(f"Обработчики сообщений настроены для группы {self.group_id}")

async def main():
    """Основная функция"""
    client = TelegramUserClient()
    try:
        if await client.setup():
            client.logger.info("Запуск клиента...")
            # Добавляем тестовое сообщение в лог
            client.logger.info("Клиент запущен и ожидает сообщения...")
            await client.client.run_until_disconnected()
    except Exception as e:
        client.logger.error(f"Критическая ошибка: {str(e)}")
        client.logger.error(f"Тип ошибки: {type(e).__name__}")
        client.logger.error(f"Трассировка:\n{traceback.format_exc()}")
    finally:
        if client.db:
            await client.db.close()
        if client.ollama_client:
            await client.ollama_client.close()
        if client.wiki_client and hasattr(client.wiki_client, 'close'):
            await client.wiki_client.close()

if __name__ == "__main__":
    asyncio.run(main()) 