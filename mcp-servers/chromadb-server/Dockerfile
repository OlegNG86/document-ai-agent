FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка uv
RUN pip install uv

# Создание рабочей директории
WORKDIR /app

# Копирование файлов проекта
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY config/ ./config/

# Установка зависимостей
RUN uv sync --frozen

# Создание пользователя для безопасности
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# Открытие порта
EXPOSE 3000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Запуск сервера
CMD ["uv", "run", "python", "-m", "chromadb_mcp_server", "--mode", "http", "--host", "0.0.0.0", "--port", "3000"]