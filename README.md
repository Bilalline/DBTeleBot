# DBTeleBot

Бот для Telegram, который анализирует сообщения в групповых чатах и создает страницы в MediaWiki на основе этих сообщений.

## Возможности

- Автоматический анализ сообщений в групповых чатах
- Создание и обновление страниц в MediaWiki
- Интеграция с Ollama для анализа текста
- Поддержка различных типов контента (текст, изображения, документы)
- Автоматическая категоризация контента

## Требования

- Python 3.8+
- Docker и Docker Compose
- Telegram API credentials (api_id и api_hash)
- MediaWiki установка
- Ollama (для анализа текста)

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/DBtelebot.git
cd DBtelebot
```

2. Создайте файл `.env` в корневой директории проекта:
```env
# Telegram
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=your_phone_number
TELEGRAM_GROUP_ID=your_group_id

# MediaWiki
MEDIAWIKI_URL=your_mediawiki_url
MEDIAWIKI_USERNAME=your_username
MEDIAWIKI_PASSWORD=your_password

# Ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama2
```

3. Создайте сессию для Telegram:
```bash
python auth.py
```
Это создаст файл `session/session.session`, который будет использоваться для авторизации.

4. Запустите бота с помощью Docker Compose:
```bash
docker-compose up -d
```

## Структура проекта

```
DBtelebot/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env
├── .env.example
├── README.md
├── auth.py              # Скрипт для создания сессии Telegram
├── main.py             # Основной код бота
├── config.py           # Конфигурация
├── database.py         # Работа с базой данных
├── ollama_client.py    # Клиент Ollama
├── wiki_client.py      # Клиент MediaWiki
├── session/            # Директория для сессий Telegram
│   └── session.session
└── logs/              # Директория для логов
    └── bot.log
```

## Конфигурация

### Telegram

1. Получите `api_id` и `api_hash` на [my.telegram.org](https://my.telegram.org)
2. Добавьте бота в группу и сделайте его администратором
3. Получите ID группы (можно через [@getidsbot](https://t.me/getidsbot))

### MediaWiki

1. Создайте учетную запись на вашей MediaWiki
2. Убедитесь, что у пользователя есть права на создание и редактирование страниц
3. Настройте права доступа в MediaWiki для работы с API

### Ollama

1. Установите Ollama согласно [официальной документации](https://ollama.ai)
2. Загрузите модель llama2:
```bash
ollama pull llama2
```

## Использование

1. Запустите бота:
```bash
docker-compose up -d
```

2. Бот начнет анализировать сообщения в указанной группе
3. Новые страницы будут создаваться в MediaWiki автоматически
4. Проверяйте логи для отслеживания работы:
```bash
docker-compose logs -f
```

## Логирование

Логи сохраняются в директории `logs/`:
- `bot.log` - основные логи бота
- `auth.log` - логи процесса авторизации

## Безопасность

- Храните `.env` файл в безопасном месте
- Не публикуйте `session.session` файл
- Регулярно обновляйте зависимости
- Используйте сложные пароли для MediaWiki

## Устранение неполадок

### Проблемы с авторизацией

1. Удалите файл `session/session.session`
2. Перезапустите Telegram на телефоне
3. Запустите `auth.py` заново
4. Следуйте инструкциям в консоли

### Проблемы с MediaWiki

1. Проверьте права доступа пользователя
2. Убедитесь, что API доступен
3. Проверьте правильность URL и учетных данных

### Проблемы с Ollama

1. Проверьте доступность Ollama:
```bash
curl http://localhost:11434/api/version
```
2. Убедитесь, что модель загружена:
```bash
ollama list
```

## Лицензия

MIT

## Автор

Ваше имя 