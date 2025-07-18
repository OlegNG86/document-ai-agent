# 🚀 Быстрый старт Document AI Agent

## Предварительные требования

✅ **Ollama уже установлена на сервере** (проверено)  
✅ **Доступные модели:**
- `qwen2.5vl:latest` - основная модель
- `qwen2.5vl:72b` - для сложных задач
- `nomic-embed-text:latest` - для эмбеддингов

## Запуск за 3 шага

### 1. Убедитесь, что Ollama запущена
```bash
# Проверка статуса
systemctl status ollama

# Если не запущена, запустите:
sudo systemctl start ollama

# Или в ручном режиме:
ollama serve
```

### 2. Запустите автоматический скрипт
```bash
./start.sh
```

Скрипт автоматически:
- Проверит доступность Ollama
- Создаст необходимые директории
- Создаст `.env` файл из примера
- Запустит Docker Compose

### 3. Начните работу
```bash
# Проверка статуса системы
docker-compose exec ai-agent poetry run python -m ai_agent.main status

# Загрузка первого документа
docker-compose exec ai-agent poetry run python -m ai_agent.main upload /path/to/document.pdf

# Интерактивный режим вопросов
docker-compose exec ai-agent poetry run python -m ai_agent.main query
```

## Архитектура системы

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Host Ubuntu   │    │   Docker Compose │    │   AI Agent App  │
│                 │    │                  │    │                 │
│  Ollama Service │◄───┤  ChromaDB        │◄───┤  Document Mgr   │
│  :11434         │    │  :8000           │    │  Query Proc     │
│                 │    │                  │    │  Session Mgr    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Основные команды

### Управление документами
```bash
# Загрузить документ
docker-compose exec ai-agent poetry run python -m ai_agent.main upload document.pdf

# Загрузить папку с документами
docker-compose exec ai-agent poetry run python -m ai_agent.main upload-batch ./documents/

# Список документов
docker-compose exec ai-agent poetry run python -m ai_agent.main docs --list

# Статистика коллекции
docker-compose exec ai-agent poetry run python -m ai_agent.main docs --stats
```

### Работа с запросами
```bash
# Интерактивный режим
docker-compose exec ai-agent poetry run python -m ai_agent.main query

# Разовый запрос
docker-compose exec ai-agent poetry run python -m ai_agent.main query --text "Ваш вопрос"
```

### Управление сессиями
```bash
# Список сессий
docker-compose exec ai-agent poetry run python -m ai_agent.main session --list

# История сессии
docker-compose exec ai-agent poetry run python -m ai_agent.main session --history SESSION_ID
```

## Настройка моделей

### Быстрый режим (по умолчанию)
```env
MODEL_SELECTION_STRATEGY=FAST
OLLAMA_DEFAULT_MODEL=qwen2.5vl:latest
```

### Автоматический выбор модели
```env
MODEL_SELECTION_STRATEGY=AUTO
OLLAMA_DEFAULT_MODEL=qwen2.5vl:latest
OLLAMA_COMPLEX_MODEL=qwen2.5vl:72b
COMPLEX_QUERY_THRESHOLD=200
```

### Максимальное качество
```env
MODEL_SELECTION_STRATEGY=QUALITY
OLLAMA_DEFAULT_MODEL=qwen2.5vl:72b
```

## Мониторинг

### Логи системы
```bash
# Логи AI Agent
docker-compose logs -f ai-agent

# Логи ChromaDB
docker-compose logs -f chromadb

# Все логи
docker-compose logs -f
```

### Статус компонентов
```bash
# Статус Ollama
curl http://localhost:11434/api/tags

# Статус ChromaDB
curl http://localhost:8000/api/v1/heartbeat

# Статус AI Agent
docker-compose exec ai-agent poetry run python -m ai_agent.main status
```

## Устранение проблем

### Ollama недоступна
```bash
# Проверка процесса
ps aux | grep ollama

# Перезапуск
sudo systemctl restart ollama

# Проверка портов
netstat -tlnp | grep 11434
```

### ChromaDB не запускается
```bash
# Пересоздание контейнера
docker-compose down
docker-compose up -d chromadb

# Очистка данных (ОСТОРОЖНО!)
docker-compose down -v
```

### AI Agent не подключается
```bash
# Проверка сети
docker-compose exec ai-agent ping host.docker.internal

# Пересборка образа
docker-compose build ai-agent
docker-compose up -d ai-agent
```

## Рекомендуемый рабочий процесс

### День 1: Настройка и тестирование
1. Запустите `./start.sh`
2. Загрузите 3-5 тестовых документов
3. Протестируйте базовые запросы

### День 2-7: Наполнение базы
1. Загрузите ключевые нормативные документы
2. Настройте стратегию выбора модели
3. Создайте шаблоны частых запросов

### Неделя 2+: Продуктивное использование
1. Интегрируйте в рабочие процессы
2. Настройте автоматическое обновление документов
3. Оптимизируйте производительность

## Полезные ссылки

- [Документация Ollama](https://ollama.ai/docs)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/)

---

**Поддержка:** При возникновении проблем проверьте логи и статус всех компонентов.
