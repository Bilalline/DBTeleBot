from telethon import TelegramClient
from telethon.sessions import StringSession
import os
from pathlib import Path
import asyncio
from loguru import logger

async def main():
    # Загрузка переменных окружения
    api_id = int(os.getenv('TELEGRAM_API_ID'))
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE')
    
    # Создание клиента
    client = TelegramClient(StringSession(), api_id, api_hash)
    
    try:
        # Подключение к Telegram
        await client.connect()
        
        # Проверка авторизации
        if not await client.is_user_authorized():
            logger.info("Требуется авторизация...")
            await client.send_code_request(phone)
            code = input("Введите код подтверждения: ")
            await client.sign_in(phone, code)
        
        # Получение информации о пользователе
        me = await client.get_me()
        logger.info(f"Авторизован как {me.first_name} (@{me.username})")
        
        # Получение строки сессии
        session_string = client.session.save()
        
        # Создание директории для сессии
        session_dir = Path("session")
        session_dir.mkdir(exist_ok=True)
        
        # Сохранение строки сессии в файл
        session_path = session_dir / "session.session"
        session_path.write_text(session_string)
        
        logger.info(f"Строка сессии сохранена в {session_path}")
        
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 