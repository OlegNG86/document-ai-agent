# Document AI Agent

Локальный AI агент на базе Ollama для работы с нормативной документацией по закупкам. Система обеспечивает загрузку документов в базу знаний, поиск по документам и проверку соответствия новых документов нормативным требованиям.

## Возможности

- 📁 **Загрузка документов**: Поддержка txt, md и docx файлов с автоматической индексацией
- 📦 **Пакетная загрузка**: Загрузка множества документов одновременно с прогресс-барами
- 🏷️ **Категоризация документов**: Система тегов и категорий (reference/normative, target, general)
- 🔍 **Умный поиск**: Векторный поиск по содержимому документов с фильтрацией по категориям
- 💬 **Интерактивные сессии**: Контекстные диалоги с сохранением истории
- ✅ **Проверка соответствия**: Целевая проверка документов против эталонных требований
- 🎯 **Интерактивный выбор**: Выбор конкретных эталонных документов для проверки
- 🔒 **Локальная обработка**: Все данные обрабатываются локально через Ollama
- 🐳 **Docker deployment**: Простое развертывание через docker-compose

## Архитектура

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Interface │────│  Query Processor │────│  Ollama Client  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         │              ┌─────────────────┐               │
         └──────────────│ Session Manager │               │
                        └─────────────────┘               │
         │                        │                        │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│Document Manager │────│    ChromaDB      │    │  Ollama Service │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Быстрый старт

### Способ 1: Docker Compose (Рекомендуемый)

1. Клонируйте репозиторий:

```bash
git clone <repository-url>
cd document-ai-agent
```

2. Запустите систему:

```bash
docker-compose up -d
```

3. Дождитесь загрузки моделей:

```bash
docker-compose logs model-init
```

4. Проверьте статус:

```bash
docker-compose exec ai-agent poetry run python -m ai_agent.main status
```

5. Начните работу:

```bash
docker-compose exec ai-agent poetry run python -m ai_agent.main query
```

### Способ 2: Локальная установка

#### Требования

- Python 3.8+
- Poetry
- Ollama (установлен и запущен)

#### Установка

1. Установите зависимости:

```bash
poetry install
```

2. Установите и запустите Ollama:

```bash
# Установка Ollama (Linux/macOS)
curl -fsSL https://ollama.ai/install.sh | sh

# Запуск сервиса
ollama serve

# Загрузка необходимых моделей
ollama pull llama3.1
ollama pull nomic-embed-text
```

3. Настройте окружение:

```bash
cp .env.example .env
# Отредактируйте .env при необходимости
```

4. Запустите агента:

```bash
poetry run docai status
```

## Использование

### Команды CLI

#### Загрузка документов

```bash
# Загрузить один документ
docai upload document.txt

# Загрузить с категорией и тегами
docai upload document.md --title "Нормативы по закупкам" --category reference --tags "нормативы,требования"

# Загрузить эталонный документ (упрощенная команда)
docai upload-reference normative-doc.txt --tags "закупки,требования"

# Пакетная загрузка документов из папки
docai batch-upload /path/to/documents

# Пакетная загрузка с категорией и тегами
docai batch-upload /path/to/documents --category reference --tags "нормативы,закупки"

# Пакетная загрузка с рекурсивным поиском
docai batch-upload /path/to/documents --recursive

# Пакетная загрузка с фильтрацией по типам файлов
docai batch-upload /path/to/documents --pattern "*.txt,*.md,*.docx"

# Предварительный просмотр без загрузки
docai batch-upload /path/to/documents --dry-run

# Пакетная загрузка с общими метаданными
docai batch-upload /path/to/documents --metadata source=ministry --category reference

# Продолжить загрузку при ошибках в отдельных файлах
docai batch-upload /path/to/documents --skip-errors
```

#### Работа с сессиями

```bash
# Интерактивный режим (создает новую сессию)
docai query

# Использовать существующую сессию
docai query --session-id SESSION_ID

# Список сессий
docai session --list

# История сессии
docai session --history SESSION_ID
```

#### Управление документами

```bash
# Список всех документов
docai docs --list

# Список документов по категории
docai docs --list --category reference
docai docs --list --category target

# Список документов по тегам
docai docs --list --tags "нормативы,требования"

# Информация о документе
docai docs --info DOC_ID

# Статистика коллекции
docai docs --stats

# Управление категориями и тегами документов
docai manage-doc DOC_ID --category reference
docai manage-doc DOC_ID --tags "новые,теги"
docai manage-doc DOC_ID --add-tag "дополнительный-тег"
docai manage-doc DOC_ID --remove-tag "старый-тег"
```

#### Проверка документов на соответствие

```bash
# Проверить документ против всех эталонных документов
docai check-document contract.txt

# Проверить с интерактивным выбором эталонных документов
docai check-document contract.txt --interactive

# Проверить против конкретных эталонных документов
docai check-document contract.txt --reference-docs "doc-id-1,doc-id-2"

# Проверить в рамках существующей сессии
docai check-document contract.txt --session-id SESSION_ID
```

#### Статус системы

```bash
# Проверить статус всех компонентов
docai status
```

### Интерактивный режим

В интерактивном режиме доступны специальные команды:

- `/help` - показать справку
- `/history` - показать историю сессии
- `/check` - режим проверки документов на соответствие
- `/exit` - выйти из режима

#### Примеры вопросов:

- "Какие требования к документации по закупкам?"
- "Что нужно указать в договоре с поставщиком?"
- "Какие документы нужны для участия в тендере?"

#### Проверка документов:

В режиме `/check` можно:

- Указать путь к файлу для проверки
- Вставить текст документа напрямую
- Получить анализ соответствия нормативным требованиям

## Конфигурация

### Переменные окружения

#### Основные настройки

| Переменная              | Значение по умолчанию    | Описание            |
| ----------------------- | ------------------------ | ------------------- |
| `OLLAMA_HOST`           | `http://localhost:11434` | URL Ollama сервиса  |
| `OLLAMA_DEFAULT_MODEL`  | `llama3.1`               | Модель по умолчанию |
| `DATA_PATH`             | `data`                   | Путь к данным       |
| `CHROMA_PATH`           | `data/chroma_db`         | Путь к ChromaDB     |
| `SESSION_TIMEOUT_HOURS` | `24`                     | Время жизни сессий  |

#### Настройки логирования

| Переменная            | Значение по умолчанию | Описание                                                |
| --------------------- | --------------------- | ------------------------------------------------------- |
| `LOG_LEVEL`           | `INFO`                | Уровень логирования (DEBUG/INFO/WARNING/ERROR/CRITICAL) |
| `LOG_DIR`             | `logs`                | Директория для файлов логов                             |
| `ENABLE_FILE_LOGGING` | `true`                | Включить запись логов в файлы                           |
| `ENABLE_JSON_LOGGING` | `false`               | Использовать JSON формат для логов                      |
| `MAX_LOG_SIZE_MB`     | `10`                  | Максимальный размер файла лога (МБ)                     |
| `LOG_BACKUP_COUNT`    | `5`                   | Количество архивных файлов логов                        |

#### Настройки производительности

| Переменная                   | Значение по умолчанию | Описание                               |
| ---------------------------- | --------------------- | -------------------------------------- |
| `SLOW_OPERATION_THRESHOLD`   | `5.0`                 | Порог медленных операций (секунды)     |
| `MEMORY_USAGE_THRESHOLD`     | `500`                 | Порог использования памяти (МБ)        |
| `ENABLE_PERFORMANCE_MONITOR` | `true`                | Включить мониторинг производительности |

### Настройка Docker

Для использования GPU в Docker (NVIDIA):

1. Установите nvidia-docker2
2. Раскомментируйте секцию deploy в docker-compose.yml для сервиса ollama

## Разработка

### Запуск тестов

```bash
# Все тесты
poetry run pytest

# Только unit тесты
poetry run pytest tests/test_models.py

# Только integration тесты
poetry run pytest tests/test_integration.py

# С покрытием
poetry run pytest --cov=ai_agent
```

### Линтинг и форматирование

```bash
# Форматирование кода
poetry run black ai_agent tests

# Проверка импортов
poetry run isort ai_agent tests

# Статический анализ
poetry run flake8 ai_agent tests

# Проверка типов
poetry run mypy ai_agent
```

### Структура проекта

```
document-ai-agent/
├── ai_agent/                 # Основной код приложения
│   ├── cli/                  # CLI интерфейс
│   ├── core/                 # Основная бизнес-логика
│   ├── models/              # Модели данных
│   ├── utils/               # Утилиты
│   └── main.py              # Точка входа
├── tests/                   # Тесты
├── data/                    # Данные (документы, ChromaDB)
├── docker-compose.yml       # Docker конфигурация
├── Dockerfile              # Docker образ
├── pyproject.toml          # Конфигурация Poetry
└── README.md               # Документация
```

## Логирование и мониторинг

### Конфигурация логирования

Система поддерживает гибкую настройку логирования через переменные окружения:

```bash
# Базовая конфигурация для разработки
export LOG_LEVEL=DEBUG
export ENABLE_FILE_LOGGING=true
export LOG_DIR=logs

# Продакшн конфигурация
export LOG_LEVEL=INFO
export ENABLE_JSON_LOGGING=true
export LOG_DIR=/var/log/ai-agent
export MAX_LOG_SIZE_MB=50
export LOG_BACKUP_COUNT=10
```

### Структура логов

Система создает следующие файлы логов:

- `ai_agent.log` - основной лог всех операций
- `errors.log` - только ошибки и критические события
- `performance.log` - метрики производительности (если включен мониторинг)

### Форматы логирования

#### Консольный вывод (цветной)

```
2024-01-15 10:30:45 - ai_agent.core.document_manager - INFO - Document uploaded successfully: abc123 [doc=abc123, time=2.34s, op=upload_document]
```

#### JSON формат (для продакшн)

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

### Мониторинг производительности

Система автоматически отслеживает:

- **Время выполнения операций** - с предупреждениями о медленных операциях
- **Использование памяти** - с отслеживанием утечек памяти
- **Системные ресурсы** - CPU, память, дисковое пространство
- **Статистику операций** - количество, успешность, средние времена

#### Просмотр метрик производительности

```bash
# Статус системы с метриками
docai status

# Детальная информация о производительности
docai performance --stats

# Медленные операции
docai performance --slow-operations

# Сброс статистики
docai performance --reset
```

### Обработка ошибок

Система использует многоуровневую обработку ошибок:

#### Категории ошибок

- **NETWORK** - сетевые ошибки и проблемы подключения
- **VALIDATION** - ошибки валидации входных данных
- **PROCESSING** - ошибки обработки документов
- **RESOURCE** - проблемы с ресурсами (память, диск)
- **CONFIGURATION** - ошибки конфигурации
- **EXTERNAL_SERVICE** - проблемы с внешними сервисами (Ollama, ChromaDB)

#### Уровни серьезности

- **LOW** - незначительные проблемы
- **MEDIUM** - проблемы, требующие внимания
- **HIGH** - серьезные ошибки, влияющие на функциональность
- **CRITICAL** - критические ошибки, требующие немедленного вмешательства

#### Retry механизмы

Система автоматически повторяет неудачные операции:

- **Экспоненциальная задержка** для сетевых запросов
- **Circuit breaker** для защиты от каскадных сбоев
- **Настраиваемые стратегии** для разных типов операций

### Примеры конфигурации логирования

#### Разработка

```bash
# .env для разработки
LOG_LEVEL=DEBUG
ENABLE_FILE_LOGGING=true
ENABLE_JSON_LOGGING=false
LOG_DIR=logs/dev
MAX_LOG_SIZE_MB=5
LOG_BACKUP_COUNT=3
SLOW_OPERATION_THRESHOLD=2.0
```

#### Продакшн

```bash
# .env для продакшн
LOG_LEVEL=INFO
ENABLE_FILE_LOGGING=true
ENABLE_JSON_LOGGING=true
LOG_DIR=/var/log/ai-agent
MAX_LOG_SIZE_MB=50
LOG_BACKUP_COUNT=30
SLOW_OPERATION_THRESHOLD=10.0
ENABLE_PERFORMANCE_MONITOR=true
```

#### Отладка

```bash
# .env для отладки
LOG_LEVEL=DEBUG
ENABLE_FILE_LOGGING=true
ENABLE_JSON_LOGGING=false
LOG_DIR=logs/debug
MAX_LOG_SIZE_MB=1
LOG_BACKUP_COUNT=2
SLOW_OPERATION_THRESHOLD=1.0
```

### Интеграция с системами мониторинга

Система поддерживает интеграцию с внешними системами мониторинга через:

- **JSON логи** для Elasticsearch/Logstash
- **Structured logging** для Prometheus/Grafana
- **Webhook уведомления** для критических ошибок
- **Метрики производительности** для систем APM

## Устранение неполадок

### Ollama не подключается

```bash
# Проверьте статус службы
ollama list

# Перезапустите Ollama
ollama serve

# Проверьте порт
curl http://localhost:11434/api/tags
```

### ChromaDB ошибки

```bash
# Очистите базу данных
rm -rf data/chroma_db

# Перезапустите приложение
docai status
```

### Docker проблемы

```bash
# Пересборка образов
docker-compose build --no-cache

# Просмотр логов
docker-compose logs -f

# Очистка volumes
docker-compose down -v
```

## Примеры использования

### Загрузка нормативной документации

```bash
# Загрузите отдельные документы
docai upload "Закон о контрактной системе.txt"
docai upload "Регламент закупок.md" --metadata category=regulation

# Или загрузите всю папку с документами сразу
docai batch-upload ./normative-docs --recursive --metadata category=regulation

# Предварительный просмотр перед загрузкой
docai batch-upload ./normative-docs --dry-run

# Проверьте загрузку
docai docs --list
```

### Проверка договора

```bash
# Запустите интерактивный режим
docai query

# В интерактивном режиме:
> /check
> /path/to/contract.txt

# Получите анализ соответствия
```

### Консультация по требованиям

```bash
# Запустите интерактивный режим
docai query

# Задайте вопросы:
> Какие документы нужны от поставщика?
> Какие сроки подачи заявок?
> Что проверять в договоре поставки?
```

### Проверка документов на соответствие

#### Подготовка эталонных документов

```bash
# Загрузите эталонные/нормативные документы
docai upload-reference "Закон о контрактной системе.txt" --tags "закон,основы"
docai upload-reference "Регламент закупок.md" --tags "процедуры,требования"
docai upload-reference "Стандарты качества.docx" --tags "качество,стандарты"

# Или загрузите обычным способом с указанием категории
docai upload normative-doc.txt --category reference --tags "нормативы"

# Проверьте загруженные эталонные документы
docai docs --list --category reference
```

#### Проверка целевых документов

```bash
# Простая проверка против всех эталонных документов
docai check-document contract-to-check.txt

# Интерактивный выбор эталонных документов
docai check-document contract-to-check.txt --interactive
# Система покажет список доступных эталонных документов
# Выберите нужные номера: 1,3,5 или 'all' для всех

# Проверка против конкретных документов (если знаете ID)
docai check-document contract-to-check.txt --reference-docs "abc123,def456"
```

#### Пример интерактивной проверки

```bash
$ docai check-document contract.txt --interactive

┌─────────────────────────────────────────────────────────────────┐
│                    Интерактивный выбор                          │
│                                                                 │
│ Выберите документы, которые будут использованы как эталон       │
│ для проверки.                                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                 Доступные эталонные документы                   │
├───┬──────────┬─────────────────────────┬──────────────┬────────┤
│ № │    ID    │        Название         │     Теги     │ Чанков │
├───┼──────────┼─────────────────────────┼──────────────┼────────┤
│ 1 │ abc123...│ Закон о контрактной...  │ закон,основы │   45   │
│ 2 │ def456...│ Регламент закупок       │ процедуры    │   32   │
│ 3 │ ghi789...│ Стандарты качества      │ качество     │   28   │
└───┴──────────┴─────────────────────────┴──────────────┴────────┘

Варианты выбора:
• Номера документов через запятую (например: 1,3,5)
• 'all' - выбрать все документы
• 'cancel' - отменить проверку

Ваш выбор: 1,2

✅ Выбрано документов: 2
  • Закон о контрактной системе
  • Регламент закупок

📋 Отчет о соответствии
═══════════════════════════════════════════════════════════════

## Анализ соответствия документа

### ✅ Соответствует требованиям:
- Указаны все обязательные реквизиты согласно ст. 34 ФЗ-44
- Соблюдены требования к предмету договора
- Правильно указаны сроки исполнения

### ⚠️ Требует внимания:
- Отсутствует указание на обеспечение исполнения договора
- Не указаны штрафные санкции за нарушение сроков

### 📚 Источники требований:
1. Закон о контрактной системе - ст. 34, 96
2. Регламент закупок - п. 4.2, 5.1

ℹ️ Уверенность: 85% | Время анализа: 3.45с | Использовано документов: 2
```

## Лицензия

MIT License - см. файл LICENSE для деталей.

## Поддержка

Для сообщения об ошибках и предложений используйте GitHub Issues.
