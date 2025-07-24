# ChromaDB MCP Server

Расширяемый MCP (Model Context Protocol) сервер с интеграцией ChromaDB для векторного поиска.

## Установка

```bash
# Установка зависимостей с помощью uv
uv sync

# Установка в режиме разработки
uv pip install -e .
```

## Использование

```bash
# Запуск сервера
uv run chromadb-mcp-server

# Или через Python модуль
uv run python -m chromadb_mcp_server
```

## Конфигурация

Конфигурация находится в файле `config/config.yaml`. Поддерживаются переменные окружения:

- `OPENAI_API_KEY` - API ключ для OpenAI эмбеддингов
- `CHROMADB_HOST` - Хост ChromaDB (по умолчанию: localhost)
- `CHROMADB_PORT` - Порт ChromaDB (по умолчанию: 8000)

## Разработка

```bash
# Установка зависимостей для разработки
uv sync --extra dev

# Запуск тестов
uv run pytest

# Форматирование кода
uv run black .
uv run isort .

# Проверка типов
uv run mypy .
```

## Архитектура

Сервер построен на модульной архитектуре:

- `core/` - Основные компоненты MCP сервера
- `tools/` - Реализации инструментов (ChromaDB и будущие)
- `services/` - Сервисы (эмбеддинги, чанкинг)
- `models/` - Модели данных Pydantic
- `config/` - Конфигурационные файлы
