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
docker-compose exec ai-agent poetry run python -m ai_agent.main upload /path/to/document.txt

# Или пакетная загрузка папки с документами
docker-compose exec ai-agent poetry run python -m ai_agent.main batch-upload /path/to/documents/

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
# Загрузить один документ
docker-compose exec ai-agent poetry run python -m ai_agent.main upload document.txt

# Загрузить с категорией и тегами
docker-compose exec ai-agent poetry run python -m ai_agent.main upload document.txt --category reference --tags "нормативы,требования"

# Загрузить эталонный документ (упрощенная команда)
docker-compose exec ai-agent poetry run python -m ai_agent.main upload-reference normative.txt --tags "закупки,требования"

# Пакетная загрузка документов из папки
docker-compose exec ai-agent poetry run python -m ai_agent.main batch-upload ./documents/

# Пакетная загрузка с категорией
docker-compose exec ai-agent poetry run python -m ai_agent.main batch-upload ./documents/ --category reference --tags "нормативы"

# Пакетная загрузка с рекурсивным поиском
docker-compose exec ai-agent poetry run python -m ai_agent.main batch-upload ./documents/ --recursive

# Пакетная загрузка с фильтрацией типов файлов
docker-compose exec ai-agent poetry run python -m ai_agent.main batch-upload ./documents/ --pattern "*.txt,*.md,*.docx"

# Предварительный просмотр без загрузки
docker-compose exec ai-agent poetry run python -m ai_agent.main batch-upload ./documents/ --dry-run

# Список всех документов
docker-compose exec ai-agent poetry run python -m ai_agent.main docs --list

# Список документов по категории
docker-compose exec ai-agent poetry run python -m ai_agent.main docs --list --category reference

# Список документов по тегам
docker-compose exec ai-agent poetry run python -m ai_agent.main docs --list --tags "нормативы,требования"

# Статистика коллекции
docker-compose exec ai-agent poetry run python -m ai_agent.main docs --stats

# Управление категориями и тегами
docker-compose exec ai-agent poetry run python -m ai_agent.main manage-doc DOC_ID --category reference
docker-compose exec ai-agent poetry run python -m ai_agent.main manage-doc DOC_ID --add-tag "новый-тег"
```

### Проверка документов на соответствие

```bash
# Проверить документ против всех эталонных документов
docker-compose exec ai-agent poetry run python -m ai_agent.main check-document contract.txt

# Интерактивный выбор эталонных документов
docker-compose exec ai-agent poetry run python -m ai_agent.main check-document contract.txt --interactive

# Проверить против конкретных эталонных документов
docker-compose exec ai-agent poetry run python -m ai_agent.main check-document contract.txt --reference-docs "doc-id-1,doc-id-2"
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

## Пакетная загрузка документов

### Основные сценарии

```bash
# Загрузить все документы из папки
docker-compose exec ai-agent poetry run python -m ai_agent.main batch-upload ./documents/

# Рекурсивный поиск во всех подпапках
docker-compose exec ai-agent poetry run python -m ai_agent.main batch-upload ./documents/ --recursive

# Загрузить только определенные типы файлов
docker-compose exec ai-agent poetry run python -m ai_agent.main batch-upload ./documents/ --pattern "*.txt,*.md"

# Добавить общие метаданные ко всем файлам
docker-compose exec ai-agent poetry run python -m ai_agent.main batch-upload ./documents/ --metadata category=legal --metadata source=ministry

# Предварительный просмотр (без загрузки)
docker-compose exec ai-agent poetry run python -m ai_agent.main batch-upload ./documents/ --dry-run

# Продолжить при ошибках в отдельных файлах
docker-compose exec ai-agent poetry run python -m ai_agent.main batch-upload ./documents/ --skip-errors
```

### Мониторинг процесса

- Прогресс-бар показывает текущий файл и процент выполнения
- Время выполнения и оставшееся время
- Подробная статистика по завершении
- Таблицы успешных и неудачных загрузок

## Проверка документов на соответствие

### Подготовка эталонных документов

```bash
# Загрузите эталонные/нормативные документы
docker-compose exec ai-agent poetry run python -m ai_agent.main upload-reference "Закон о контрактной системе.txt" --tags "закон,основы"
docker-compose exec ai-agent poetry run python -m ai_agent.main upload-reference "Регламент закупок.md" --tags "процедуры,требования"

# Или пакетная загрузка эталонных документов
docker-compose exec ai-agent poetry run python -m ai_agent.main batch-upload ./normative-docs/ --category reference --tags "нормативы"

# Проверьте загруженные эталонные документы
docker-compose exec ai-agent poetry run python -m ai_agent.main docs --list --category reference
```

### Проверка целевых документов

```bash
# Простая проверка против всех эталонных документов
docker-compose exec ai-agent poetry run python -m ai_agent.main check-document contract-to-check.txt

# Интерактивный выбор эталонных документов
docker-compose exec ai-agent poetry run python -m ai_agent.main check-document contract-to-check.txt --interactive

# Проверка против конкретных документов (если знаете ID)
docker-compose exec ai-agent poetry run python -m ai_agent.main check-document contract-to-check.txt --reference-docs "abc123,def456"
```

### Пример рабочего процесса проверки

1. **Подготовка эталонной базы:**

   ```bash
   # Загрузите все нормативные документы
   docker-compose exec ai-agent poetry run python -m ai_agent.main batch-upload ./normative-docs/ --category reference --tags "нормативы"
   ```

2. **Проверка документа:**

   ```bash
   # Интерактивная проверка с выбором эталонов
   docker-compose exec ai-agent poetry run python -m ai_agent.main check-document contract.txt --interactive
   ```

3. **Анализ результатов:**
   - Система покажет детальный отчет о соответствии
   - Укажет найденные нарушения и несоответствия
   - Предоставит ссылки на источники требований
   - Даст рекомендации по устранению проблем

## Рекомендуемый рабочий процесс

### День 1: Настройка и тестирование

1. Запустите `./start.sh`
2. Загрузите 3-5 тестовых документов с разными категориями
3. Протестируйте базовые запросы и проверку документов

### День 2-7: Наполнение базы

1. Используйте пакетную загрузку для ключевых нормативных документов как `reference`
2. Настройте стратегию выбора модели
3. Создайте шаблоны частых запросов
4. Протестируйте проверку документов на соответствие

### Неделя 2+: Продуктивное использование

1. Интегрируйте проверку документов в рабочие процессы
2. Настройте автоматическое обновление документов с помощью batch-upload
3. Используйте категоризацию для организации документов
4. Оптимизируйте производительность

## Полезные ссылки

- [Документация Ollama](https://ollama.ai/docs)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/)

---

**Поддержка:** При возникновении проблем проверьте логи и статус всех компонентов.
