#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Запуск полного проекта Document AI Agent ===${NC}"

# Создание необходимых директорий
echo -e "${YELLOW}Создание необходимых директорий...${NC}"
mkdir -p data/documents
mkdir -p data/chroma_db
mkdir -p logs
mkdir -p visualization/data/decision_trees

# Установка прав доступа
echo -e "${YELLOW}Установка прав доступа...${NC}"
chmod -R 777 data
chmod -R 777 logs
chmod -R 777 visualization/data

# Запуск всех сервисов
echo -e "${YELLOW}Запуск всех сервисов...${NC}"

# Остановка и удаление всех контейнеров проекта
docker-compose down

# Принудительное удаление контейнера визуализации, если он существует
echo -e "${YELLOW}Проверка и удаление существующих контейнеров...${NC}"
if [ "$(docker ps -a -q -f name=ai-agent-visualization)" ]; then
    echo -e "${YELLOW}Удаление существующего контейнера ai-agent-visualization...${NC}"
    docker rm -f ai-agent-visualization
fi

# Запуск всех сервисов
docker-compose up -d

# Проверка статуса
echo -e "${YELLOW}Проверка статуса контейнеров...${NC}"
docker-compose ps

echo -e "\n${GREEN}=== Проект запущен ===${NC}"
echo -e "ChromaDB доступен по адресу: ${BLUE}http://localhost:8000${NC}"
echo -e "Визуализация деревьев решений доступна по адресу: ${BLUE}http://10.50.50.10:8501${NC}"
echo -e "\nДля использования AI агента выполните:"
echo -e "${YELLOW}docker-compose exec ai-agent poetry run python -m ai_agent.main query${NC}"
echo -e "\nДля проверки документа с визуализацией:"
echo -e "${YELLOW}docker-compose exec ai-agent poetry run python -m ai_agent.main check-document /path/to/document.txt --web-visualization${NC}"