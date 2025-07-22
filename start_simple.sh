#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Запуск упрощенной версии системы визуализации ===${NC}"

# Остановка всех контейнеров
echo -e "${YELLOW}Остановка всех контейнеров...${NC}"
docker-compose down

# Удаление старого контейнера и образа
echo -e "${YELLOW}Удаление старого контейнера и образа...${NC}"
docker rm -f ai-agent-visualization 2>/dev/null || true
docker rmi document-ai-agent-v3_decision-tree-viz 2>/dev/null || true

# Создание тестовых данных
echo -e "${YELLOW}Создание тестовых данных...${NC}"
mkdir -p visualization/data/decision_trees

# Создание примера JSON файла для тестирования
cat > visualization/data/decision_trees/example_tree.json << 'EOL'
{
  "id": "abcd1234-5678-90ab-cdef-1234567890ab",
  "query_type": "general_question",
  "timestamp": "2025-07-20T12:34:56",
  "root": {
    "id": "node-1",
    "label": "Обработка запроса",
    "description": "Начальная точка обработки пользовательского запроса",
    "probability": 1.0,
    "children": [
      {
        "id": "node-2",
        "label": "Найден релевантный контекст",
        "description": "Найдены документы, релевантные запросу",
        "probability": 0.8,
        "children": []
      },
      {
        "id": "node-3",
        "label": "Контекст не найден",
        "description": "Релевантные документы не найдены",
        "probability": 0.2,
        "children": []
      }
    ]
  },
  "statistics": {
    "total_nodes": 3,
    "total_paths": 2,
    "max_depth": 2,
    "generation_time": 0.45
  }
}
EOL

# Запуск с упрощенным docker-compose файлом
echo -e "${YELLOW}Запуск с упрощенным docker-compose файлом...${NC}"
docker-compose -f docker-compose.simple.yml up -d

# Проверка статуса
echo -e "${YELLOW}Проверка статуса контейнеров...${NC}"
docker-compose -f docker-compose.simple.yml ps

echo -e "\n${GREEN}=== Упрощенная версия запущена ===${NC}"
echo -e "Веб-интерфейс должен быть доступен по адресу: ${BLUE}http://10.50.50.10:8501${NC}"
echo -e "Проверьте логи контейнера: ${YELLOW}docker-compose -f docker-compose.simple.yml logs -f decision-tree-viz${NC}"