#!/bin/bash

# Скрипт для запуска системы визуализации деревьев решений

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Запуск системы визуализации деревьев решений ===${NC}"

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Ошибка: Docker не установлен${NC}"
    echo "Установите Docker и Docker Compose перед запуском"
    exit 1
fi

# Проверка наличия Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Ошибка: Docker Compose не установлен${NC}"
    echo "Установите Docker Compose перед запуском"
    exit 1
fi

# Создание директории для данных, если она не существует
mkdir -p visualization/data/decision_trees
echo -e "${GREEN}✓${NC} Директория для данных создана"

# Экспорт переменных окружения
export VISUALIZATION_ENABLED=true
export VISUALIZATION_URL=http://localhost:8501
export DECISION_TREE_EXPORT_PATH=./visualization/data/decision_trees
echo -e "${GREEN}✓${NC} Переменные окружения установлены"

# Запуск Docker Compose
echo -e "${YELLOW}Запуск контейнеров...${NC}"
docker-compose up -d

# Проверка статуса
echo -e "${YELLOW}Проверка статуса контейнеров...${NC}"
docker-compose ps

echo -e "\n${GREEN}=== Система визуализации запущена ===${NC}"
echo -e "Веб-интерфейс доступен по адресу: ${BLUE}http://localhost:8501${NC}"
echo -e "Используйте ${YELLOW}--web-visualization${NC} при запуске команд для включения визуализации"
echo -e "Например: ${YELLOW}docai query --web-visualization${NC}"
echo -e "\nДля остановки системы выполните: ${YELLOW}docker-compose down${NC}"