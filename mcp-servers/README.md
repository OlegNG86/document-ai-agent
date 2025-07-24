# MCP Servers

Коллекция MCP серверов для различных сервисов, развернутых в Docker контейнерах.

## Быстрый старт

1. Скопируйте файл переменных окружения:

```bash
cp .env.example .env
```

2. Убедитесь, что Ollama запущен на хост-системе с необходимыми моделями:

```bash
ollama serve

# Загрузка моделей
ollama pull nomic-embed-text:latest      # для эмбеддингов
ollama pull qwen2.5vl:latest            # основная модель
ollama pull qwen2.5vl:72b               # сложная модель (опционально)
```

3. Запустите сервисы:

```bash
docker-compose up -d
```

4. Проверьте статус сервисов:

```bash
docker-compose ps
```

## Доступные сервисы

### ChromaDB MCP Server

- **URL**: http://localhost:3000
- **Health Check**: http://localhost:3000/health
- **MCP Tools**: http://localhost:3000/mcp/tools

### ChromaDB

- **URL**: http://localhost:8000
- **Admin UI**: http://localhost:8000 (если доступно)

## API Endpoints

### MCP Server

- `GET /health` - Проверка состояния сервера
- `GET /mcp/tools` - Список доступных MCP инструментов
- `POST /mcp/tools/{tool_name}` - Вызов конкретного инструмента

### Пример использования

```bash
# Проверка здоровья сервера
curl http://localhost:3000/health

# Получение списка инструментов
curl http://localhost:3000/mcp/tools

# Вызов инструмента поиска
curl -X POST http://localhost:3000/mcp/tools/chromadb_search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "collection": "documents",
    "n_results": 5
  }'
```

## Конфигурация

Конфигурация сервисов находится в:

- `chromadb-server/config/config.yaml` - Основная конфигурация MCP сервера
- `docker-compose.yml` - Конфигурация Docker сервисов
- `.env` - Переменные окружения

## Разработка

Для разработки отдельного сервера:

```bash
cd chromadb-server
uv sync --extra dev
uv run python -m chromadb_mcp_server --mode http --host localhost --port 3000
```

## Логи

Просмотр логов:

```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f chromadb-mcp-server
docker-compose logs -f chromadb
```

## Остановка

```bash
# Остановка сервисов
docker-compose down

# Остановка с удалением данных
docker-compose down -v
```
