import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger
from telethon import TelegramClient
from telethon.sessions import StringSession

# Настройка логирования
logger.add("logs/auth.log", rotation="1 day", retention="7 days", level="INFO")

# Загрузка переменных окружения
load_dotenv()

async def main():
    """Создание сессии для Telegram"""
    try:
        # Получение параметров из .env
        api_id = int(os.getenv("TELEGRAM_API_ID"))
        api_hash = os.getenv("TELEGRAM_API_HASH")
        phone = os.getenv("TELEGRAM_PHONE")

        if not all([api_id, api_hash, phone]):
            raise ValueError("Не установлены все необходимые параметры в .env")

        # Создание директории для сессии
        session_dir = Path("session")
        session_dir.mkdir(exist_ok=True)

        # Создание клиента
        client = TelegramClient(
            StringSession(),
            api_id,
            api_hash,
            device_model="DBTeleBot",
            system_version="Linux",
            app_version="1.0",
            lang_code="ru"
        )

        # Подключение и авторизация
        logger.info("Подключение к Telegram...")
        await client.connect()

        if not await client.is_user_authorized():
            logger.info("Отправка кода подтверждения...")
            await client.send_code_request(phone)
            
            code = input("Введите код подтверждения: ")
            await client.sign_in(phone, code)

        # Получение информации о пользователе
        me = await client.get_me()
        logger.info(f"Успешная авторизация как {me.first_name} (@{me.username})")

        # Сохранение сессии
        session_string = client.session.save()
        session_file = session_dir / "session.session"
        with open(session_file, 'wb') as f:
            f.write(session_string.encode('utf-8'))
        logger.info(f"Сессия сохранена в {session_file}")

        await client.disconnect()

    except Exception as e:
        logger.error(f"Ошибка при создании сессии: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 