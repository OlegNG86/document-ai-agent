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

## Поддерживаемые форматы файлов

Система поддерживает следующие форматы документов:

| Формат               | Расширение | Особенности                      |
| -------------------- | ---------- | -------------------------------- |
| **Plain Text**       | `.txt`     | Базовое извлечение текста        |
| **Markdown**         | `.md`      | Извлечение с подсчетом элементов |
| **Microsoft Word**   | `.docx`    | Текст, таблицы, метаданные       |
| **PDF Document**     | `.pdf`     | Текст по страницам               |
| **Rich Text Format** | `.rtf`     | Форматированный текст            |

### Просмотр поддерживаемых форматов

```bash
# Показать все поддерживаемые форматы
docker-compose exec ai-agent poetry run python -m ai_agent.main formats
```

### Опции извлечения текста

```bash
# Показать извлеченный текст при загрузке
docker-compose exec ai-agent poetry run python -m ai_agent.main upload document.pdf --show-text

# Показать текст при проверке документа
docker-compose exec ai-agent poetry run python -m ai_agent.main check-document contract.docx --show-text

# Показать текст при пакетной загрузке
docker-compose exec ai-agent poetry run python -m ai_agent.main batch-upload ./documents/ --show-text
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
docker-compose exec ai-agent poetry run python -m ai_agent.main batch-upload ./documents/ --pattern "*.txt,*.md,*.docx,*.pdf,*.rtf"

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

# Запрос с деревом решений
docker-compose exec ai-agent poetry run python -m ai_agent.main query --show-decision-tree
```

### 🌳 Анализ процесса принятия решений

Система включает мощную функциональность визуализации дерева решений для понимания логики обработки запросов:

```bash
# Показать дерево решений для обычного запроса
docker-compose exec ai-agent poetry run python -m ai_agent.main query --show-decision-tree

# Показать дерево решений при проверке документа
docker-compose exec ai-agent poetry run python -m ai_agent.main check-document contract.docx --show-decision-tree
```

#### Настройка через переменные окружения

Добавьте в `.env` файл:

```env
# Глобально включить дерево решений
SHOW_DECISION_TREE=true

# Уровень детализации (brief/full/extended)
DECISION_TREE_DETAIL=full

# Отключить цвета для логов
DECISION_TREE_COLORS=false

# Максимальная ширина вывода
DECISION_TREE_WIDTH=120
```

#### Пример вывода дерева решений

```
==================================================
🌳 АНАЛИЗ ПРОЦЕССА ПРИНЯТИЯ РЕШЕНИЙ
==================================================
Decision Tree: general_question
===============================

Обработка запроса (1.00)
├── Найден релевантный контекст (0.80)
│   └─ Найдены документы, релевантные запросу
│   ├── Прямой ответ из документов (0.70)
│   │   └─ Ответ найден непосредственно в документах
│   │   ├── Высокая точность (0.80)
│   │   └── Средняя точность (0.20)
│   ├── Синтез информации (0.25)
│   │   └─ Требуется объединение информации из нескольких источников
│   └── Интерпретация требуется (0.05)
│       └─ Требуется интерпретация сложной информации
├── Контекст частично релевантен (0.15)
│   └─ Найдены частично релевантные документы
│   ├── Частичный ответ (0.60)
│   └── Общие рекомендации (0.40)
└── Контекст не найден (0.05)
    └─ Релевантные документы не найдены
    └── Сообщить об отсутствии данных (1.00)

Statistics:
  Total nodes: 12
  Total paths: 6
  Tree depth: 4
  Query type: general_question
```

#### Цветовое кодирование вероятностей:

- 🟢 **Зеленый** (≥0.7): Высокая вероятность
- 🟡 **Желтый** (0.4-0.69): Средняя вероятность
- 🔴 **Красный** (<0.4): Низкая вероятность

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

## Мониторинг и логирование

### Настройка логирования

Система поддерживает гибкую настройку логирования. Создайте или обновите `.env` файл:

```bash
# Базовая конфигурация
LOG_LEVEL=INFO
ENABLE_FILE_LOGGING=true
LOG_DIR=logs
MAX_LOG_SIZE_MB=10
LOG_BACKUP_COUNT=5

# Для отладки
LOG_LEVEL=DEBUG
ENABLE_JSON_LOGGING=false

# Для продакшн
LOG_LEVEL=INFO
ENABLE_JSON_LOGGING=true
LOG_DIR=/var/log/ai-agent
MAX_LOG_SIZE_MB=50
```

### Логи системы

```bash
# Логи AI Agent (Docker)
docker-compose logs -f ai-agent

# Логи ChromaDB
docker-compose logs -f chromadb

# Все логи
docker-compose logs -f

# Файлы логов (если включено ENABLE_FILE_LOGGING)
tail -f logs/ai_agent.log      # Основной лог
tail -f logs/errors.log        # Только ошибки
```

### Структура логов

Система создает следующие файлы:

- `ai_agent.log` - все операции системы
- `errors.log` - только ошибки и критические события
- `performance.log` - метрики производительности

### Мониторинг производительности

```bash
# Статус системы с метриками производительности
docker-compose exec ai-agent poetry run python -m ai_agent.main status

# Детальная информация о производительности
docker-compose exec ai-agent poetry run python -m ai_agent.main performance --stats

# Медленные операции
docker-compose exec ai-agent poetry run python -m ai_agent.main performance --slow

# Сброс статистики производительности
docker-compose exec ai-agent poetry run python -m ai_agent.main performance --reset
```

### Статус компонентов

```bash
# Статус Ollama
curl http://localhost:11434/api/tags

# Статус ChromaDB
curl http://localhost:8000/api/v1/heartbeat

# Полный статус AI Agent с метриками
docker-compose exec ai-agent poetry run python -m ai_agent.main status
```

### Примеры логов

#### Консольный вывод (цветной)

```
2024-01-15 10:30:45 - ai_agent.core.document_manager - INFO - Document uploaded successfully: abc123 [doc=abc123, time=2.34s, op=upload_document]
```

#### JSON формат (для анализа)

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "level": "INFO",
  "logger": "ai_agent.core.document_manager",
  "message": "Document uploaded successfully: abc123",
  "document_id": "abc123",
  "processing_time": 2.34,
  "operation": "upload_document"
}
```

### Обработка ошибок

Система автоматически:

- **Повторяет неудачные операции** с экспоненциальной задержкой
- **Защищает от каскадных сбоев** с помощью circuit breaker
- **Классифицирует ошибки** по категориям и уровням серьезности
- **Предоставляет рекомендации** по устранению проблем

#### Категории ошибок:

- `NETWORK` - проблемы с сетью и подключениями
- `VALIDATION` - ошибки валидации данных
- `PROCESSING` - ошибки обработки документов
- `EXTERNAL_SERVICE` - проблемы с Ollama/ChromaDB

#### Пример обработки ошибки:

```
2024-01-15 10:30:45 - ai_agent.core.ollama_client - WARNING - Retry 1/3 for generate_response after 2.00s: Connection timeout
2024-01-15 10:30:47 - ai_agent.core.ollama_client - INFO - Generated response successfully [time=1.23s, retry_count=1]
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

## Настройка производительности

### Оптимизация кэширования

Система использует многоуровневое кэширование для ускорения работы:

```bash
# Статистика кэша
docker-compose exec ai-agent poetry run python -m ai_agent.main cache --stats

# Очистка кэша
docker-compose exec ai-agent poetry run python -m ai_agent.main cache --clear

# Очистка устаревших записей
docker-compose exec ai-agent poetry run python -m ai_agent.main cache --cleanup
```

### Конфигурации производительности

Выберите подходящую конфигурацию для вашей нагрузки:

#### Разработка и тестирование

```bash
cp examples/performance-configs/development.env .env.performance
```

Оптимизировано для:

- Быстрый запуск и отладка
- Минимальное потребление ресурсов
- Короткое время жизни кэша

#### Продуктивная среда

```bash
cp examples/performance-configs/production.env .env.performance
```

Оптимизировано для:

- Стабильная работа под нагрузкой
- Балансированное использование ресурсов
- Эффективное кэширование

#### Высокие нагрузки

```bash
cp examples/performance-configs/high-load.env .env.performance
```

Оптимизировано для:

- Максимальная пропускная способность
- Большое количество одновременных запросов
- Агрессивное кэширование

### Мониторинг производительности

```bash
# Общая статистика производительности
docker-compose exec ai-agent poetry run python -m ai_agent.main performance --stats

# Медленные операции
docker-compose exec ai-agent poetry run python -m ai_agent.main performance --slow

# Статистика конкретной операции
docker-compose exec ai-agent poetry run python -m ai_agent.main performance --stats --operation search_similar_chunks

# Сброс статистики
docker-compose exec ai-agent poetry run python -m ai_agent.main performance --reset
```

### Оптимизация чанкинга

Система автоматически оптимизирует размер чанков в зависимости от типа документа:

- **Юридические документы**: Меньшие чанки (600-800 символов) для точных ссылок
- **Технические документы**: Большие чанки (1000-1500 символов) для сохранения контекста
- **Структурированные документы**: Адаптивные чанки с сохранением структуры списков
- **Повествовательные тексты**: Стандартные чанки (800-1000 символов)

### Асинхронная обработка

Для больших документов (>50KB) автоматически включается асинхронная обработка:

```bash
# Статистика асинхронной обработки
docker-compose exec ai-agent poetry run python -m ai_agent.main status
```

### Рекомендации по оптимизации

#### Для небольших систем (1-2 пользователя)

```env
ASYNC_MAX_WORKERS=2
CACHE_QUERY_MAX_SIZE=200
CACHE_EMBEDDING_MAX_SIZE=500
PERFORMANCE_SLOW_THRESHOLD=3.0
```

#### Для средних систем (5-10 пользователей)

```env
ASYNC_MAX_WORKERS=4
CACHE_QUERY_MAX_SIZE=500
CACHE_EMBEDDING_MAX_SIZE=1000
PERFORMANCE_SLOW_THRESHOLD=5.0
```

#### Для больших систем (10+ пользователей)

```env
ASYNC_MAX_WORKERS=8
CACHE_QUERY_MAX_SIZE=1000
CACHE_EMBEDDING_MAX_SIZE=2000
PERFORMANCE_SLOW_THRESHOLD=10.0
```

### Мониторинг ресурсов

Система автоматически отслеживает:

- **CPU**: Предупреждения при >80%, критические при >95%
- **Память**: Предупреждения при >80%, критические при >95%
- **Диск**: Предупреждения при >85%, критические при >95%
- **Время отклика**: Логирование медленных операций

### Устранение проблем производительности

#### Медленные запросы

1. Проверьте статистику кэша: `cache --stats`
2. Увеличьте размер кэша в конфигурации
3. Проверьте медленные операции: `performance --slow`

#### Высокое потребление памяти

1. Уменьшите размер кэша
2. Сократите количество воркеров
3. Очистите кэш: `cache --clear`

#### Медленная обработка документов

1. Увеличьте количество воркеров
2. Оптимизируйте размеры чанков
3. Включите асинхронную обработку для меньших документов

## Полезные ссылки

- [Документация Ollama](https://ollama.ai/docs)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/)

---

**Поддержка:** При возникновении проблем проверьте логи и статус всех компонентов.
