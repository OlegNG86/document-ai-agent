# Document AI Agent

Локальный AI агент на базе Ollama для работы с нормативной документацией по закупкам. Система обеспечивает загрузку документов в базу знаний, поиск по документам и проверку соответствия новых документов нормативным требованиям.

## Возможности

- 📁 **Загрузка документов**: Поддержка txt и md файлов с автоматической индексацией
- 🔍 **Умный поиск**: Векторный поиск по содержимому документов с использованием ChromaDB
- 💬 **Интерактивные сессии**: Контекстные диалоги с сохранением истории
- ✅ **Проверка соответствия**: Анализ документов на соответствие нормативным требованиям
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
# Загрузить документ
docai upload document.txt

# Загрузить с метаданными
docai upload document.md --title "Нормативы по закупкам" --metadata category=normative
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
# Список документов
docai docs --list

# Информация о документе
docai docs --info DOC_ID

# Статистика коллекции
docai docs --stats
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

| Переменная | Значение по умолчанию | Описание |
|------------|----------------------|----------|
| `OLLAMA_HOST` | `http://localhost:11434` | URL Ollama сервиса |
| `OLLAMA_DEFAULT_MODEL` | `llama3.1` | Модель по умолчанию |
| `DATA_PATH` | `data` | Путь к данным |
| `CHROMA_PATH` | `data/chroma_db` | Путь к ChromaDB |
| `LOG_LEVEL` | `INFO` | Уровень логирования |
| `SESSION_TIMEOUT_HOURS` | `24` | Время жизни сессий |

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
# Загрузите документы с нормативами
docai upload "Закон о контрактной системе.txt"
docai upload "Регламент закупок.md" --metadata category=regulation

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

## Лицензия

MIT License - см. файл LICENSE для деталей.

## Поддержка

Для сообщения об ошибках и предложений используйте GitHub Issues.