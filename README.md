# Document AI Agent

Локальный AI агент на базе Ollama для работы с нормативной документацией по закупкам. Система обеспечивает загрузку документов в базу знаний, поиск по документам и проверку соответствия новых документов нормативным требованиям.

## Возможности

- 📁 **Загрузка документов**: Поддержка TXT, MD, DOCX, PDF и RTF файлов с автоматической индексацией
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

## Развертывание на Ubuntu сервере

### Полная инструкция по установке на Ubuntu Server

#### Системные требования

- **ОС**: Ubuntu 20.04 LTS или новее
- **RAM**: Минимум 8 GB (рекомендуется 16 GB для больших моделей)
- **Диск**: Минимум 50 GB свободного места
- **CPU**: 4+ ядра (рекомендуется)
- **GPU**: Опционально (NVIDIA с поддержкой CUDA для ускорения)

#### Шаг 1: Подготовка системы

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка необходимых пакетов
sudo apt install -y curl wget git build-essential software-properties-common

# Установка Python 3.9+ (если не установлен)
sudo apt install -y python3 python3-pip python3-venv

# Проверка версии Python
python3 --version
```

#### Шаг 2: Установка Docker и Docker Compose

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Перезагрузка для применения изменений группы
sudo reboot
```

#### Шаг 3: Клонирование проекта

```bash
# Клонирование репозитория
git clone https://github.com/your-username/document-ai-agent.git
cd document-ai-agent

# Проверка содержимого
ls -la
```

#### Шаг 4: Настройка окружения

```bash
# Создание файла окружения
cp .env.example .env

# Редактирование конфигурации (используйте nano или vim)
nano .env
```

**Пример конфигурации для сервера (.env):**

```bash
# Основные настройки
OLLAMA_HOST=http://ollama:11434
OLLAMA_DEFAULT_MODEL=llama3.1
DATA_PATH=/app/data
CHROMA_PATH=/app/data/chroma_db
SESSION_TIMEOUT_HOURS=24

# Настройки логирования для продакшн
LOG_LEVEL=INFO
LOG_DIR=/app/logs
ENABLE_FILE_LOGGING=true
ENABLE_JSON_LOGGING=true
MAX_LOG_SIZE_MB=50
LOG_BACKUP_COUNT=30

# Настройки производительности
SLOW_OPERATION_THRESHOLD=10.0
MEMORY_USAGE_THRESHOLD=1000
ENABLE_PERFORMANCE_MONITOR=true

# Настройки дерева решений
SHOW_DECISION_TREE=false
DECISION_TREE_DETAIL=brief
DECISION_TREE_COLORS=false
```

#### Шаг 5: Запуск системы

```bash
# Запуск в фоновом режиме
docker-compose up -d

# Просмотр логов запуска
docker-compose logs -f

# Проверка статуса контейнеров
docker-compose ps
```

#### Шаг 6: Ожидание загрузки моделей

```bash
# Мониторинг загрузки моделей (может занять 10-30 минут)
docker-compose logs -f model-init

# Проверка доступности Ollama
curl http://localhost:11434/api/tags

# Проверка статуса системы
docker-compose exec ai-agent poetry run python -m ai_agent.main status
```

#### Шаг 7: Первый запуск и тестирование

```bash
# Интерактивный режим
docker-compose exec ai-agent poetry run python -m ai_agent.main query

# Загрузка тестового документа
echo "Тестовый документ для проверки системы" > test.txt
docker-compose exec ai-agent poetry run python -m ai_agent.main upload /app/test.txt

# Проверка списка документов
docker-compose exec ai-agent poetry run python -m ai_agent.main docs --list
```

### Настройка для продакшн среды

#### Настройка systemd сервиса

```bash
# Создание systemd сервиса
sudo nano /etc/systemd/system/document-ai-agent.service
```

**Содержимое файла сервиса:**

```ini
[Unit]
Description=Document AI Agent
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/document-ai-agent
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

```bash
# Перемещение проекта в системную директорию
sudo mv document-ai-agent /opt/
sudo chown -R $USER:$USER /opt/document-ai-agent

# Активация сервиса
sudo systemctl daemon-reload
sudo systemctl enable document-ai-agent
sudo systemctl start document-ai-agent

# Проверка статуса
sudo systemctl status document-ai-agent
```

#### Настройка Nginx (опционально)

```bash
# Установка Nginx
sudo apt install -y nginx

# Создание конфигурации
sudo nano /etc/nginx/sites-available/document-ai-agent
```

**Конфигурация Nginx:**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Активация конфигурации
sudo ln -s /etc/nginx/sites-available/document-ai-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Настройка файрвола

```bash
# Настройка UFW
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Проверка статуса
sudo ufw status
```

### Мониторинг и обслуживание

#### Просмотр логов

```bash
# Логи всех сервисов
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f ai-agent
docker-compose logs -f ollama

# Логи системы
sudo journalctl -u document-ai-agent -f
```

#### Обновление системы

```bash
# Переход в директорию проекта
cd /opt/document-ai-agent

# Получение обновлений
git pull origin main

# Пересборка и перезапуск
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Проверка статуса
docker-compose ps
```

#### Резервное копирование

```bash
# Создание скрипта резервного копирования
sudo nano /usr/local/bin/backup-ai-agent.sh
```

**Скрипт резервного копирования:**

```bash
#!/bin/bash
BACKUP_DIR="/backup/document-ai-agent"
DATE=$(date +%Y%m%d_%H%M%S)

# Создание директории для бэкапов
mkdir -p $BACKUP_DIR

# Остановка сервисов
cd /opt/document-ai-agent
docker-compose stop

# Архивирование данных
tar -czf $BACKUP_DIR/data_$DATE.tar.gz data/
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz logs/

# Запуск сервисов
docker-compose start

# Удаление старых бэкапов (старше 30 дней)
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
# Настройка прав и cron
sudo chmod +x /usr/local/bin/backup-ai-agent.sh
sudo crontab -e

# Добавить строку для ежедневного бэкапа в 2:00
0 2 * * * /usr/local/bin/backup-ai-agent.sh >> /var/log/ai-agent-backup.log 2>&1
```

### Устранение неполадок на сервере

#### Проверка ресурсов

```bash
# Использование памяти и CPU
htop
docker stats

# Использование диска
df -h
du -sh /opt/document-ai-agent/data/

# Проверка сетевых подключений
netstat -tlnp | grep :11434
```

#### Очистка системы

```bash
# Очистка Docker
docker system prune -a

# Очистка логов
sudo journalctl --vacuum-time=7d

# Очистка старых данных (осторожно!)
# docker-compose exec ai-agent rm -rf /app/data/chroma_db
```

#### Перезапуск сервисов

```bash
# Полный перезапуск
sudo systemctl restart document-ai-agent

# Или через docker-compose
cd /opt/document-ai-agent
docker-compose restart

# Перезапуск отдельного сервиса
docker-compose restart ai-agent
docker-compose restart ollama
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

## Поддерживаемые форматы файлов

Система поддерживает следующие форматы документов:

| Формат               | Расширение | Возможности извлечения                                         |
| -------------------- | ---------- | -------------------------------------------------------------- |
| **Plain Text**       | `.txt`     | Базовое извлечение текста с поддержкой различных кодировок     |
| **Markdown**         | `.md`      | Извлечение текста с подсчетом заголовков, ссылок и блоков кода |
| **Microsoft Word**   | `.docx`    | Текст, таблицы, метаданные документа, изображения              |
| **PDF Document**     | `.pdf`     | Текст по страницам, метаданные документа                       |
| **Rich Text Format** | `.rtf`     | Извлечение форматированного текста                             |

### Особенности обработки форматов

#### DOCX файлы

- Извлечение текста из параграфов и таблиц
- Сохранение структуры таблиц с разделителями
- Подсчет количества таблиц, изображений и секций
- Извлечение метаданных документа (автор, дата создания, заголовок)

#### PDF файлы

- Извлечение текста постранично с маркерами страниц
- Поддержка метаданных PDF (автор, создатель, дата создания)
- Обработка зашифрованных PDF (только для чтения метаданных)
- Лучше всего работает с текстовыми PDF

#### RTF файлы

- Автоматическое удаление RTF форматирования
- Поддержка различных кодировок
- Конвертация в чистый текст

### Опции извлечения текста

```bash
# Показать извлеченный текст при загрузке
docai upload document.pdf --show-text

# Показать текст при проверке документа
docai check-document contract.docx --show-text

# Показать текст при пакетной загрузке
docai batch-upload /path/to/docs --show-text
```

### Просмотр поддерживаемых форматов

```bash
# Показать все поддерживаемые форматы
docai formats
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
docai batch-upload /path/to/documents --pattern "*.txt,*.md,*.docx,*.pdf,*.rtf"

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

## Анализ процесса принятия решений

Система включает в себя мощную функциональность визуализации дерева решений, которая позволяет понять, как AI агент принимает решения при обработке запросов и проверке документов.

### Возможности системы дерева решений

- 🌳 **Визуализация процесса принятия решений** - ASCII-дерево с цветовым кодированием
- 📊 **Анализ вероятностей** - расчет вероятностей для каждого пути принятия решений
- 🎯 **Категоризация запросов** - автоматическое определение типа запроса
- 📈 **Различные уровни детализации** - краткий, полный и расширенный режимы
- 🔍 **Анализ путей решений** - детальный анализ выбранных путей
- ⚙️ **Гибкая настройка** - управление через CLI опции и переменные окружения

### Веб-интерфейс визуализации

Система также предоставляет интерактивный веб-интерфейс для визуализации деревьев решений:

- 🖥️ **Интерактивные графы** - масштабирование, перемещение, подробная информация при наведении
- 📊 **Анализ путей** - таблица всех возможных путей с вероятностями
- 📁 **Экспорт** - сохранение визуализаций в PNG, SVG, PDF форматах
- 🔍 **Фильтрация** - выбор деревьев по типу запроса и времени создания

#### Доступ к веб-интерфейсу

```bash
# Запуск с включенной визуализацией
docai query --web-visualization

# Проверка документа с визуализацией
docai check-document contract.txt --web-visualization
```

После выполнения команды с флагом `--web-visualization` система выведет ссылку на веб-интерфейс, где можно будет просмотреть интерактивную визуализацию дерева решений.

Веб-интерфейс доступен по адресу: http://localhost:8501

### Использование дерева решений

#### CLI опции

```bash
# Включить дерево решений для запросов
docai query --show-decision-tree

# Включить дерево решений для проверки документов
docai check-document contract.txt --show-decision-tree
```

#### Переменные окружения

```bash
# Глобальное включение дерева решений
export SHOW_DECISION_TREE=true

# Уровень детализации (brief/full/extended)
export DECISION_TREE_DETAIL=full

# Отключить цвета (для логов)
export DECISION_TREE_COLORS=false

# Максимальная ширина дерева
export DECISION_TREE_WIDTH=120
```

### Типы запросов и деревья решений

Система автоматически определяет тип запроса и строит соответствующее дерево решений:

#### 1. Общие вопросы (GENERAL_QUESTION)

```
Decision Tree: general_question
==============================

└── Обработка запроса (1.00)
    ├── Найден релевантный контекст (0.80)
    │   ├── Прямой ответ из документов (0.70)
    │   │   ├── Высокая точность (0.80)
    │   │   └── Средняя точность (0.20)
    │   ├── Синтез информации (0.25)
    │   └── Интерпретация требуется (0.05)
    ├── Контекст частично релевантен (0.15)
    │   ├── Частичный ответ (0.60)
    │   └── Общие рекомендации (0.40)
    └── Контекст не найден (0.05)
        └── Сообщить об отсутствии данных (1.00)
```

#### 2. Проверка соответствия (COMPLIANCE_CHECK)

```
Decision Tree: compliance_check
===============================

└── Проверка соответствия (1.00)
    ├── Эталонные документы найдены (0.90)
    │   ├── Полная проверка (0.70)
    │   │   ├── Полное соответствие (0.30)
    │   │   ├── Соответствие с замечаниями (0.50)
    │   │   ├── Частичное соответствие (0.15)
    │   │   └── Несоответствие (0.05)
    │   ├── Выборочная проверка (0.20)
    │   └── Базовая проверка (0.10)
    └── Частичная база нормативов (0.10)
```

### Уровни детализации

#### Краткий режим (brief)

Показывает только основную структуру дерева с вероятностями.

#### Полный режим (full)

Включает описания узлов и статистику дерева.

#### Расширенный режим (extended)

Добавляет метаданные узлов и детальную статистику.

### Пример вывода дерева решений

```bash
$ docai query --show-decision-tree
> Какие требования к договору поставки?

[Обычный ответ AI агента...]

==================================================
🌳 АНАЛИЗ ПРОЦЕССА ПРИНЯТИЯ РЕШЕНИЙ
==================================================

Decision Tree: general_question
===============================

└── Обработка запроса (1.00)
    └─ Начальная точка обработки пользовательского запроса
    ├── Найден релевантный контекст (0.80)
    │   └─ Найдены документы, релевантные запросу
    │   ├── Прямой ответ из документов (0.70)
    │   │   └─ Ответ найден непосредственно в документах
    │   │   ├── Высокая точность (0.80)
    │   │   │   └─ Ответ с высокой степенью точности
    │   │   └── Средняя точность (0.20)
    │   │       └─ Ответ требует дополнительной проверки
    │   ├── Синтез информации (0.25)
    │   │   └─ Требуется объединение информации из нескольких источников
    │   └── Интерпретация требуется (0.05)
    │       └─ Требуется интерпретация сложной информации
    ├── Контекст частично релевантен (0.15)
    │   └─ Найдены частично релевантные документы
    │   ├── Частичный ответ (0.60)
    │   │   └─ Можно дать частичный ответ
    │   └── Общие рекомендации (0.40)
    │       └─ Предоставить общие рекомендации
    └── Контекст не найден (0.05)
        └─ Релевантные документы не найдены
        └── Сообщить об отсутствии данных (1.00)
            └─ Честно сообщить об отсутствии информации

Statistics:
  Total nodes: 12
  Total paths: 6
  Tree depth: 4
  Query type: general_question
```

### Интерпретация дерева решений

#### Цветовое кодирование вероятностей

- 🟢 **Зеленый (≥0.7)** - Высокая вероятность
- 🟡 **Желтый (0.4-0.69)** - Средняя вероятность
- 🔴 **Красный (<0.4)** - Низкая вероятность

#### Анализ путей

Система показывает наиболее вероятные пути принятия решений:

```
Selected Path:
--------------
1. Обработка запроса (1.00) →
2. Найден релевантный контекст (0.80) →
3. Прямой ответ из документов (0.70) →
4. Высокая точность (0.80)

Total path probability: 0.448
```

### Настройка и кастомизация

#### Отключение цветов для логирования

```bash
export NO_COLOR=1
# или
export DECISION_TREE_COLORS=false
```

#### Настройка ширины вывода

```bash
export DECISION_TREE_WIDTH=100
```

#### Интеграция в скрипты

```bash
# Сохранение дерева решений в файл
docai query --show-decision-tree > analysis.log 2>&1
```

### Применение в анализе

Дерево решений помогает:

1. **Понять логику AI** - как система принимает решения
2. **Оптимизировать запросы** - формулировать вопросы для лучших результатов
3. **Диагностировать проблемы** - понять, почему получен определенный ответ
4. **Улучшить базу знаний** - определить недостающие документы
5. **Настроить систему** - корректировать пороги и параметры

### Примеры использования в различных сценариях

#### Анализ качества ответов

```bash
# Сравнение деревьев для разных формулировок вопроса
docai query --show-decision-tree
> Требования к договору
# vs
> Какие требования предъявляются к договору поставки согласно нормативам?
```

#### Диагностика проблем с базой знаний

```bash
# Если дерево показывает низкие вероятности нахождения контекста
docai query --show-decision-tree
> [ваш вопрос]
# Анализируйте путь "Контекст не найден" - возможно, нужно добавить документы
```

#### Оптимизация проверки документов

```bash
# Анализ процесса проверки соответствия
docai check-document contract.txt --show-decision-tree
# Изучите пути проверки для понимания критериев оценки
```

## Лицензия

MIT License - см. файл LICENSE для деталей.

## Поддержка

Для сообщения об ошибках и предложений используйте GitHub Issues.

## MCP Server Integration

Система включает в себя MCP (Model Context Protocol) сервер для интеграции с внешними AI агентами и IDE.

### ChromaDB MCP Server

MCP сервер предоставляет HTTP API для взаимодействия с ChromaDB векторной базой данных:

- **URL**: http://localhost:3000
- **Health Check**: http://localhost:3000/health
- **MCP Tools**: http://localhost:3000/mcp/tools

### Доступные MCP инструменты

#### chromadb_search

Поиск документов в ChromaDB по семантическому сходству.

**Параметры:**

- `query` (string, обязательный) - поисковый запрос
- `collection` (string, обязательный) - имя коллекции
- `n_results` (integer, опциональный) - количество результатов (по умолчанию: 5)

**Пример использования:**

```bash
curl -X POST http://localhost:3000/mcp/tools/chromadb_search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "требования к договору поставки",
    "collection": "documents",
    "n_results": 5
  }'
```

### Конфигурация MCP сервера

MCP сервер настраивается через переменные окружения:

```bash
# ChromaDB подключение
CHROMADB_HOST=chromadb
CHROMADB_PORT=8000

# OpenAI API для эмбеддингов
OPENAI_API_KEY=your_api_key_here

# MCP сервер настройки
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=3000
LOG_LEVEL=INFO
```

### Интеграция с IDE

Для интеграции с Kiro IDE или другими MCP-совместимыми инструментами:

1. Убедитесь, что MCP сервер запущен:

```bash
curl http://localhost:3000/health
```

2. Настройте MCP клиент для подключения к `http://localhost:3000`

3. Используйте доступные инструменты для поиска в документах

### Разработка MCP инструментов

Структура MCP сервера позволяет легко добавлять новые инструменты:

```
mcp-servers/chromadb-server/
├── src/chromadb_mcp_server/
│   ├── core/          # Основные компоненты MCP
│   ├── tools/         # Реализации инструментов
│   ├── services/      # Сервисы (эмбеддинги, чанкинг)
│   └── models/        # Модели данных
├── config/            # Конфигурационные файлы
├── tests/             # Тесты
└── Dockerfile         # Docker образ
```

Для добавления нового инструмента:

1. Создайте класс инструмента в `tools/`
2. Зарегистрируйте инструмент в основном сервере
3. Добавьте соответствующие тесты
4. Обновите конфигурацию

### Логи MCP сервера

Просмотр логов MCP сервера:

```bash
# Логи MCP сервера
docker-compose logs -f chromadb-mcp-server

# Проверка статуса всех сервисов
docker-compose ps
```
