#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Создание тестового дерева решений ===${NC}"

# Создание директории, если она не существует
mkdir -p visualization/data/decision_trees

# Создание тестового JSON файла
cat > visualization/data/decision_trees/test_tree_$(date +%Y%m%d_%H%M%S).json << 'EOL'
{
  "id": "test-tree-001",
  "query_type": "general_question",
  "timestamp": "2024-01-15T10:30:45Z",
  "root": {
    "id": "node-1",
    "label": "Обработка запроса",
    "description": "Начальная точка обработки пользовательского запроса",
    "probability": 1.0,
    "children": [
      {
        "id": "node-2",
        "label": "Найден релевантный контекст",
        "description": "В базе данных найдены документы, релевантные запросу пользователя",
        "probability": 0.8,
        "children": [
          {
            "id": "node-4",
            "label": "Высокая релевантность",
            "description": "Найденные документы имеют высокую степень релевантности",
            "probability": 0.9,
            "children": []
          },
          {
            "id": "node-5",
            "label": "Средняя релевантность",
            "description": "Найденные документы имеют среднюю степень релевантности",
            "probability": 0.1,
            "children": []
          }
        ]
      },
      {
        "id": "node-3",
        "label": "Контекст не найден",
        "description": "В базе данных не найдены релевантные документы",
        "probability": 0.2,
        "children": [
          {
            "id": "node-6",
            "label": "Общий ответ",
            "description": "Предоставление общего ответа на основе базовых знаний",
            "probability": 0.7,
            "children": []
          },
          {
            "id": "node-7",
            "label": "Запрос уточнения",
            "description": "Запрос дополнительной информации у пользователя",
            "probability": 0.3,
            "children": []
          }
        ]
      }
    ]
  },
  "statistics": {
    "total_nodes": 7,
    "total_paths": 4,
    "max_depth": 3,
    "generation_time": 0.45
  }
}
EOL

echo -e "${GREEN}✓ Тестовое дерево решений создано${NC}"
echo -e "${YELLOW}Файл сохранен в: visualization/data/decision_trees/${NC}"

# Проверка создания файла
if ls visualization/data/decision_trees/test_tree_*.json > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Файл успешно создан${NC}"
    ls -la visualization/data/decision_trees/test_tree_*.json
else
    echo -e "${RED}✗ Ошибка при создании файла${NC}"
fi

echo -e "\n${BLUE}=== Создание завершено ===${NC}"
echo -e "Теперь вы можете открыть http://localhost:8501 и увидеть тестовое дерево решений"