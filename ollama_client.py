import aiohttp
import json
import logging
from typing import Dict, Any, Optional
import traceback

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, url: str, model: str):
        self.base_url = url.rstrip('/')
        self.model = model
        self.session = None
        logger.info(f"Инициализация клиента Ollama для {self.base_url}")

    async def setup(self):
        """Инициализация клиента Ollama"""
        logger.info(f"Начало инициализации клиента Ollama для {self.base_url}")
        
        try:
            logger.info("Создание HTTP сессии...")
            self.session = aiohttp.ClientSession()
            logger.info("HTTP сессия успешно создана")
            
            # Проверка доступности модели
            logger.info("Проверка доступности модели Ollama...")
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    models = await response.json()
                    if any(model['name'] == self.model for model in models.get('models', [])):
                        logger.info("Модель Ollama доступна")
                    else:
                        raise ValueError(f"Модель {self.model} не найдена на сервере")
                else:
                    raise ConnectionError(f"Ошибка при проверке моделей: {response.status}")
            
            logger.info(f"Успешное подключение к Ollama: {self.base_url}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации клиента Ollama: {str(e)}")
            if self.session:
                await self.session.close()
            raise

    async def analyze_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Анализ текста с помощью Ollama"""
        try:
            logger.info(f"Начало анализа текста длиной {len(text)} символов")
            
            # Формируем промпт для анализа
            prompt = f"""Проанализируй следующий текст и верни результат в формате JSON:
            {{
                "title": "Краткий заголовок (до 5 слов)",
                "summary": "Краткое описание (1-2 предложения)",
                "categories": ["категория1", "категория2"],
                "tags": ["тег1", "тег2"]
            }}

            Текст для анализа:
            {text}

            Верни ТОЛЬКО JSON, без дополнительного текста."""

            logger.info("Отправка запроса к Ollama...")
            response = await self.session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            logger.info("Получен ответ от Ollama")

            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Ошибка API Ollama: {response.status} - {error_text}")
                return None

            result = await response.json()
            logger.info(f"Получен ответ от Ollama API: {result}")

            # Извлекаем JSON из ответа
            response_text = result.get('response', '')
            logger.info(f"Получен ответ от модели:\n{response_text}")

            # Пытаемся найти JSON в ответе
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                logger.error("Не удалось найти JSON в ответе")
                return None

            json_text = response_text[json_start:json_end]
            logger.info(f"Извлеченный JSON:\n{json_text}")

            # Очищаем JSON от возможных лишних символов
            json_text = json_text.strip()
            if json_text.startswith('```json'):
                json_text = json_text[7:]
            if json_text.endswith('```'):
                json_text = json_text[:-3]
            json_text = json_text.strip()

            logger.info(f"Очищенный JSON:\n{json_text}")

            # Парсим JSON
            try:
                result = json.loads(json_text)
                logger.info(f"Успешно распарсен JSON: {result}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга JSON: {str(e)}")
                logger.error(f"Проблемный JSON:\n{json_text}")
                return None

        except Exception as e:
            logger.error(f"Ошибка при анализе текста: {str(e)}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            logger.error(f"Трассировка:\n{traceback.format_exc()}")
            return None

    async def close(self):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()
            self.session = None 