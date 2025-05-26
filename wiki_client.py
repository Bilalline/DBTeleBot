import mwclient
from loguru import logger
from typing import Optional, Dict, Any
import asyncio
import traceback
import os
from pathlib import Path

class WikiClient:
    def __init__(self):
        self.site: Optional[mwclient.Site] = None
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self.wiki_url: Optional[str] = None

    async def setup(self, username: str, password: str, wiki_url: str) -> bool:
        """Инициализация клиента MediaWiki"""
        try:
            logger.info(f"Начало инициализации клиента MediaWiki для {wiki_url}")
            self.username = username
            self.password = password
            self.wiki_url = wiki_url

            # Подключение к MediaWiki в отдельном потоке
            logger.info("Создание подключения к MediaWiki...")
            
            # Извлекаем домен из URL
            domain = wiki_url.replace('https://', '').replace('http://', '')
            
            # Создаем сайт с отключенным интерактивным вводом
            self.site = await asyncio.to_thread(
                mwclient.Site,
                domain,
                path='/',  # Путь к API (mwclient автоматически добавит api.php)
                scheme='https',  # Используем HTTPS
                clients_useragent='DBTeleBot/1.0'
            )
            logger.info("Подключение к MediaWiki успешно создано")
            
            # Авторизация в отдельном потоке
            logger.info("Выполнение авторизации в MediaWiki...")
            await asyncio.to_thread(
                self.site.login,
                username,
                password
            )
            logger.info("Авторизация в MediaWiki успешно выполнена")
            
            logger.info(f"Успешное подключение к MediaWiki: {wiki_url}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при подключении к MediaWiki: {str(e)}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            logger.error(f"Трассировка:\n{traceback.format_exc()}")
            return False

    async def create_page(self, title: str, content: str, categories: list = None) -> bool:
        """Создание новой страницы"""
        try:
            if not self.site:
                raise ValueError("Клиент MediaWiki не инициализирован")

            logger.info(f"Создание страницы: {title}")
            logger.info(f"Содержимое страницы:\n{content}")
            
            page = self.site.pages[title]
            
            # Добавление категорий
            if categories:
                content += "\n\n[[Category:" + "]]\n[[Category:".join(categories) + "]]"
                logger.info(f"Добавлены категории: {categories}")

            # Создание страницы в отдельном потоке
            logger.info(f"Сохранение страницы {title} в MediaWiki...")
            await asyncio.to_thread(
                page.save,
                content,
                "Создание страницы ботом"
            )
            logger.info(f"Создана новая страница: {title}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при создании страницы {title}: {str(e)}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            logger.error(f"Трассировка:\n{traceback.format_exc()}")
            return False

    async def edit_page(self, title: str, content: str, append: bool = True) -> bool:
        """Редактирование существующей страницы"""
        try:
            if not self.site:
                raise ValueError("Клиент MediaWiki не инициализирован")

            logger.info(f"Редактирование страницы: {title}")
            logger.info(f"Новое содержимое:\n{content}")
            
            page = self.site.pages[title]
            
            if not page.exists:
                logger.info(f"Страница {title} не существует, создаем новую")
                return await self.create_page(title, content)

            # Получение текущего содержимого в отдельном потоке
            logger.info(f"Получение текущего содержимого страницы {title}")
            current_content = await asyncio.to_thread(page.text)
            logger.info(f"Текущее содержимое страницы:\n{current_content}")
            
            # Добавление нового содержимого
            if append:
                new_content = current_content + "\n\n" + content
                logger.info("Режим добавления: новое содержимое будет добавлено в конец")
            else:
                new_content = content
                logger.info("Режим перезаписи: текущее содержимое будет заменено")

            # Сохранение изменений в отдельном потоке
            logger.info(f"Сохранение изменений страницы {title}")
            await asyncio.to_thread(
                page.save,
                new_content,
                "Обновление страницы ботом"
            )
            logger.info(f"Обновлена страница: {title}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при редактировании страницы {title}: {str(e)}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            logger.error(f"Трассировка:\n{traceback.format_exc()}")
            return False

    async def upload_file(self, title: str, file_path: str, description: str = "") -> bool:
        """Загрузка файла на MediaWiki"""
        try:
            if not self.site:
                raise ValueError("Клиент MediaWiki не инициализирован")

            # Проверка существования файла
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"Файл не найден: {file_path}")

            logger.info(f"Загрузка файла: {title}")
            
            # Открываем файл в бинарном режиме
            with open(file_path, 'rb') as file:
                await asyncio.to_thread(
                    self.site.upload,
                    file,
                    title,
                    description
                )
            
            logger.info(f"Загружен файл: {title}")
            return True

        except FileNotFoundError as e:
            logger.error(f"Файл не найден: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при загрузке файла {title}: {str(e)}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            logger.error(f"Трассировка:\n{traceback.format_exc()}")
            return False 