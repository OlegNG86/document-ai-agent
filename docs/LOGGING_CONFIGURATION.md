# Конфигурация логирования AI Agent

## Обзор

AI Agent использует расширенную централизованную систему логирования с поддержкой:

- Многоуровневого логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Цветного консольного вывода для разработки
- JSON формата для продакшн и анализа
- Автоматической ротации файлов логов
- Контекстного логирования с метаданными
- Мониторинга производительности и здоровья системы
- Интеллектуальной обработки ошибок с retry механизмами
- Централизованной системы уведомлений об ошибках
- Автоматической классификации и статистики ошибок
- Мониторинга состояния системы в реальном времени

## Переменные окружения

### Основные настройки логирования

| Переменная            | По умолчанию | Описание                            |
| --------------------- | ------------ | ----------------------------------- |
| `LOG_LEVEL`           | `INFO`       | Уровень логирования                 |
| `ENABLE_FILE_LOGGING` | `true`       | Включить запись в файлы             |
| `ENABLE_JSON_LOGGING` | `false`      | Использовать JSON формат            |
| `LOG_DIR`             | `logs`       | Директория для файлов логов         |
| `MAX_LOG_SIZE_MB`     | `10`         | Максимальный размер файла лога (МБ) |
| `LOG_BACKUP_COUNT`    | `5`          | Количество архивных файлов          |

### Мониторинг производительности

| Переменная                   | По умолчанию | Описание                               |
| ---------------------------- | ------------ | -------------------------------------- |
| `SLOW_OPERATION_THRESHOLD`   | `5.0`        | Порог медленных операций (секунды)     |
| `MEMORY_USAGE_THRESHOLD`     | `500`        | Порог использования памяти (МБ)        |
| `ENABLE_PERFORMANCE_MONITOR` | `true`       | Включить мониторинг производительности |

### Расширенная обработка ошибок

| Переменная                   | По умолчанию | Описание                                    |
| ---------------------------- | ------------ | ------------------------------------------- |
| `ENABLE_ERROR_NOTIFICATIONS` | `true`       | Включить централизованные уведомления       |
| `ERROR_RATE_THRESHOLD`       | `10`         | Максимум ошибок за период до предупреждения |
| `ERROR_RATE_WINDOW_MINUTES`  | `5`          | Временное окно для подсчета ошибок (минуты) |
| `NETWORK_TIMEOUT`            | `30`         | Таймаут сетевых операций (секунды)          |
| `OLLAMA_TIMEOUT`             | `120`        | Таймаут операций Ollama (секунды)           |
| `MAX_RETRY_ATTEMPTS`         | `5`          | Максимальное количество повторов            |
| `RETRY_BASE_DELAY`           | `1.0`        | Базовая задержка между повторами (секунды)  |

### Мониторинг здоровья системы

| Переменная                  | По умолчанию | Описание                             |
| --------------------------- | ------------ | ------------------------------------ |
| `ENABLE_HEALTH_MONITORING`  | `true`       | Включить мониторинг здоровья системы |
| `HEALTH_CHECK_INTERVAL`     | `60`         | Интервал проверок здоровья (секунды) |
| `CPU_WARNING_THRESHOLD`     | `80`         | Порог предупреждения CPU (%)         |
| `CPU_CRITICAL_THRESHOLD`    | `95`         | Критический порог CPU (%)            |
| `MEMORY_WARNING_THRESHOLD`  | `80`         | Порог предупреждения памяти (%)      |
| `MEMORY_CRITICAL_THRESHOLD` | `95`         | Критический порог памяти (%)         |

## Уровни логирования

### DEBUG

- Детальная информация для отладки
- Все операции с временными метками
- Параметры функций и промежуточные результаты
- Рекомендуется только для разработки

### INFO

- Основные операции системы
- Успешные завершения операций
- Статистика и метрики
- Подходит для продакшн

### WARNING

- Потенциальные проблемы
- Retry попытки
- Медленные операции
- Высокое использование ресурсов

### ERROR

- Ошибки, не приводящие к остановке
- Неудачные операции после всех retry
- Проблемы с внешними сервисами

### CRITICAL

- Критические ошибки системы
- Проблемы, требующие немедленного вмешательства
- Ошибки запуска приложения

## Структура файлов логов

При включенном `ENABLE_FILE_LOGGING=true` создаются следующие файлы:

```
logs/
├── ai_agent.log          # Основной лог всех операций
├── ai_agent.log.1        # Архивный файл (ротация)
├── ai_agent.log.2        # Архивный файл (ротация)
├── errors.log            # Только ERROR и CRITICAL
├── errors.log.1          # Архивный файл ошибок
└── performance.log       # Метрики производительности (если включен мониторинг)
```

## Форматы логирования

### Консольный формат (разработка)

```
2024-01-15 10:30:45 - ai_agent.core.document_manager - INFO - Document uploaded successfully: abc123 [doc=abc123, time=2.34s, op=upload_document]
```

**Структура:**

- `Timestamp` - время события
- `Logger name` - модуль, создавший запись
- `Level` - уровень логирования
- `Message` - основное сообщение
- `[Context]` - дополнительная контекстная информация

### JSON формат (продакшн)

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "level": "INFO",
  "logger": "ai_agent.core.document_manager",
  "message": "Document uploaded successfully: abc123",
  "module": "document_manager",
  "function": "upload_document",
  "line": 156,
  "document_id": "abc123",
  "processing_time": 2.34,
  "operation": "upload_document",
  "category": "reference",
  "content_length": 15420
}
```

## Контекстное логирование

Система автоматически добавляет контекстную информацию:

### Операционный контекст

- `operation` - название операции
- `processing_time` - время выполнения
- `session_id` - идентификатор сессии
- `document_id` - идентификатор документа

### Технический контекст

- `module` - модуль Python
- `function` - функция
- `line` - номер строки
- `retry_count` - количество повторов
- `error_code` - код ошибки

### Бизнес-контекст

- `category` - категория документа
- `tags` - теги документа
- `model` - используемая модель
- `query_length` - длина запроса

## Примеры конфигураций

### Разработка

```bash
# .env для разработки
LOG_LEVEL=DEBUG
ENABLE_FILE_LOGGING=true
ENABLE_JSON_LOGGING=false
LOG_DIR=logs/dev
MAX_LOG_SIZE_MB=5
LOG_BACKUP_COUNT=3
SLOW_OPERATION_THRESHOLD=2.0
MEMORY_USAGE_THRESHOLD=300
```

**Особенности:**

- Подробное логирование (DEBUG)
- Цветной консольный вывод
- Небольшие файлы логов
- Низкие пороги для предупреждений

### Продакшн

```bash
# .env для продакшн
LOG_LEVEL=INFO
ENABLE_FILE_LOGGING=true
ENABLE_JSON_LOGGING=true
LOG_DIR=/var/log/ai-agent
MAX_LOG_SIZE_MB=50
LOG_BACKUP_COUNT=30
SLOW_OPERATION_THRESHOLD=10.0
MEMORY_USAGE_THRESHOLD=1000
```

**Особенности:**

- Оптимальный уровень логирования (INFO)
- JSON формат для анализа
- Большие файлы с длительным хранением
- Высокие пороги для стабильности

### Тестирование

```bash
# .env для тестов
LOG_LEVEL=WARNING
ENABLE_FILE_LOGGING=false
ENABLE_JSON_LOGGING=false
LOG_DIR=logs/test
MAX_LOG_SIZE_MB=1
LOG_BACKUP_COUNT=2
SLOW_OPERATION_THRESHOLD=1.0
```

**Особенности:**

- Минимальное логирование (WARNING+)
- Без файлов логов
- Быстрое выполнение тестов

## Мониторинг производительности

### Автоматическое отслеживание

Система автоматически отслеживает:

- **Время выполнения операций**
- **Использование памяти**
- **Системные ресурсы** (CPU, память, диск)
- **Статистику операций**

### Предупреждения о производительности

```
2024-01-15 10:30:45 - ai_agent.core.document_manager - WARNING - Operation upload_document completed in 12.34s (SLOW) [time=12.34s, threshold=5.0s]
```

### Метрики в логах

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "level": "INFO",
  "message": "Operation completed",
  "operation": "search_similar_chunks",
  "processing_time": 2.34,
  "memory_before": 245.6,
  "memory_after": 267.8,
  "memory_delta": 22.2,
  "cpu_percent": 15.4
}
```

## Обработка ошибок

### Классификация ошибок

Все ошибки классифицируются по:

#### Категориям:

- `NETWORK` - сетевые проблемы
- `VALIDATION` - ошибки валидации
- `PROCESSING` - ошибки обработки
- `RESOURCE` - проблемы с ресурсами
- `CONFIGURATION` - ошибки конфигурации
- `EXTERNAL_SERVICE` - проблемы с внешними сервисами

#### Уровням серьезности:

- `LOW` - незначительные проблемы
- `MEDIUM` - требуют внимания
- `HIGH` - серьезные ошибки
- `CRITICAL` - критические проблемы

### Retry механизмы

```
2024-01-15 10:30:45 - ai_agent.core.ollama_client - WARNING - Retry 1/3 for generate_response after 2.00s: Connection timeout [op=generate_response, retry_count=1, delay=2.0]
2024-01-15 10:30:47 - ai_agent.core.ollama_client - WARNING - Retry 2/3 for generate_response after 4.00s: Connection timeout [op=generate_response, retry_count=2, delay=4.0]
2024-01-15 10:30:51 - ai_agent.core.ollama_client - INFO - Generated response successfully [op=generate_response, time=1.23s, retry_count=2]
```

### Структурированные ошибки

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "level": "ERROR",
  "message": "Document upload failed: File not found",
  "error_code": "DOCUMENT_FILE_NOT_FOUND",
  "category": "VALIDATION",
  "severity": "HIGH",
  "operation": "upload_document",
  "file_path": "/path/to/missing/file.txt",
  "suggestions": [
    "Check if the file path is correct",
    "Verify file permissions",
    "Ensure the file exists"
  ]
}
```

## Интеграция с внешними системами

### Elasticsearch/Logstash

JSON логи можно легко интегрировать с ELK stack:

```bash
# Filebeat конфигурация
filebeat.inputs:
- type: log
  paths:
    - /var/log/ai-agent/*.log
  json.keys_under_root: true
  json.add_error_key: true
```

### Prometheus/Grafana

Метрики производительности можно экспортировать:

```python
# Пример экспорта метрик
from prometheus_client import Counter, Histogram

operation_counter = Counter('ai_agent_operations_total', 'Total operations', ['operation', 'status'])
operation_duration = Histogram('ai_agent_operation_duration_seconds', 'Operation duration', ['operation'])
```

### Webhook уведомления

Для критических ошибок можно настроить webhook:

```bash
# .env
ENABLE_ERROR_WEBHOOKS=true
ERROR_WEBHOOK_URL=https://your-monitoring-system.com/webhook
ERROR_WEBHOOK_TOKEN=your-secret-token
```

## Лучшие практики

### Разработка

1. Используйте `LOG_LEVEL=DEBUG` для отладки
2. Включите цветной вывод в консоли
3. Используйте небольшие файлы логов
4. Мониторьте производительность с низкими порогами

### Продакшн

1. Используйте `LOG_LEVEL=INFO` или `WARNING`
2. Включите JSON формат для анализа
3. Настройте ротацию логов
4. Мониторьте дисковое пространство
5. Интегрируйте с системами мониторинга

### Безопасность

1. Включите `MASK_SENSITIVE_DATA=true`
2. Ограничьте доступ к файлам логов
3. Регулярно очищайте старые логи
4. Не логируйте пароли и токены

### Производительность

1. Используйте асинхронное логирование для высоких нагрузок
2. Настройте буферизацию записи
3. Мониторьте размер файлов логов
4. Используйте сжатие для архивных файлов

## Устранение проблем

### Логи не создаются

```bash
# Проверьте права доступа
ls -la logs/
chmod 755 logs/

# Проверьте переменные окружения
echo $LOG_DIR
echo $ENABLE_FILE_LOGGING
```

### Большие файлы логов

```bash
# Уменьшите размер файлов
export MAX_LOG_SIZE_MB=10

# Увеличьте ротацию
export LOG_BACKUP_COUNT=10

# Повысьте уровень логирования
export LOG_LEVEL=WARNING
```

### Медленная работа

```bash
# Отключите подробное логирование
export LOG_LEVEL=INFO

# Отключите файловое логирование для тестов
export ENABLE_FILE_LOGGING=false

# Отключите мониторинг производительности
export ENABLE_PERFORMANCE_MONITOR=false
```
