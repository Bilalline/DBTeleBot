FROM python:3.11-slim

WORKDIR /app

# Установка необходимых пакетов
RUN apt-get update && apt-get install -y \
    iputils-ping \
    net-tools \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание необходимых директорий
RUN mkdir -p /app/data /app/logs /app/session

# Установка прав на директории
RUN chmod -R 777 /app/data /app/logs /app/session

# Копирование файлов проекта
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Установка прав на файлы проекта
RUN chmod -R 755 /app

# Создание томов
VOLUME ["/app/data", "/app/logs", "/app/session"]

# Запуск бота
CMD ["python", "main.py"] 