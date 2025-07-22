# Инструкция по запуску проекта Document AI Agent

## Подготовка

1. **Очистите репозиторий от отладочных файлов**:

   ```bash
   ./cleanup.sh
   ```

2. **Убедитесь, что установлены необходимые зависимости**:
   - Docker
   - Docker Compose
   - Ollama (для локальных LLM моделей)

## Запуск проекта

1. **Запустите полный проект**:

   ```bash
   ./start_project.sh
   ```

   Этот скрипт выполнит следующие действия:

   - Создаст необходимые директории
   - Установит правильные права доступа
   - Запустит все сервисы через docker-compose
   - Проверит статус контейнеров

2. **Проверьте доступность сервисов**:
   - ChromaDB: http://localhost:8000
   - Визуализация деревьев решений: http://10.50.50.10:8501

## Использование AI агента

1. **Интерактивный режим**:

   ```bash
   docker-compose exec ai-agent poetry run python -m ai_agent.main query
   ```

2. **Загрузка документов**:

   ```bash
   docker-compose exec ai-agent poetry run python -m ai_agent.main upload /path/to/document.txt
   ```

3. **Проверка документа с визуализацией**:

   ```bash
   docker-compose exec ai-agent poetry run python -m ai_agent.main check-document /path/to/document.txt --web-visualization
   ```

4. **Пакетная загрузка документов**:
   ```bash
   docker-compose exec ai-agent poetry run python -m ai_agent.main batch-upload /path/to/documents
   ```

## Визуализация деревьев решений

Для включения визуализации деревьев решений используйте флаг `--web-visualization` при выполнении команд:

```bash
# Запрос с визуализацией
docker-compose exec ai-agent poetry run python -m ai_agent.main query --web-visualization

# Проверка документа с визуализацией
docker-compose exec ai-agent poetry run python -m ai_agent.main check-document /path/to/document.txt --web-visualization
```

После выполнения команды с флагом `--web-visualization` система выведет ссылку на веб-интерфейс, где можно будет просмотреть интерактивную визуализацию дерева решений.

## Остановка проекта

```bash
docker-compose down
```

## Устранение неполадок

1. **Если сервис визуализации недоступен**:

   ```bash
   # Проверьте логи контейнера
   docker-compose logs -f decision-tree-viz

   # Перезапустите контейнер
   docker-compose restart decision-tree-viz
   ```

2. **Если нужно пересоздать контейнеры**:

   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

3. **Если возникают проблемы с доступом к файлам**:

   ```bash
   # Установите правильные права доступа
   chmod -R 777 data
   chmod -R 777 logs
   chmod -R 777 visualization/data
   ```

4. **Если нужно проверить работу сервиса визуализации**:

   ```bash
   # Проверка доступности сервиса
   curl -I http://10.50.50.10:8501

   # Проверка наличия файлов деревьев решений
   docker-compose exec decision-tree-viz ls -la /app/data/decision_trees
   ```
