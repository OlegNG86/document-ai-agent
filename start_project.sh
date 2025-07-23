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

# Запуск всех сервисов с пересборкой
docker-compose up -d --build

# Проверка статуса
echo -e "${YELLOW}Проверка статуса контейнеров...${NC}"
docker-compose ps

echo -e "\n${GREEN}=== Проект запущен ===${NC}"
echo -e "ChromaDB доступен по адресу: ${BLUE}http://localhost:8000${NC}"
echo -e "Визуализация деревьев решений доступна по адресу: ${BLUE}http://localhost:8501${NC}"

echo -e "\n${GREEN}=== Основные команды ===${NC}"
echo -e "Для получения справки по всем командам:"
echo -e "${YELLOW}docker-compose exec ai-agent poetry run docai --help${NC}"

echo -e "\nДля интерактивного режима запросов:"
echo -e "${YELLOW}docker-compose exec ai-agent poetry run docai query${NC}"

echo -e "\nДля проверки документа на соответствие:"
echo -e "${YELLOW}docker-compose exec ai-agent poetry run docai check-document /app/data/contracts-to-check/perfect_contract.txt --web-visualization${NC}"

echo -e "\nДля загрузки документов в базу знаний:"
echo -e "${YELLOW}docker-compose exec ai-agent poetry run docai upload /path/to/document.txt${NC}"

echo -e "\nДля загрузки эталонных документов:"
echo -e "${YELLOW}docker-compose exec ai-agent poetry run docai upload-reference /path/to/reference.txt${NC}"

echo -e "\nДля просмотра состояния системы:"
echo -e "${YELLOW}docker-compose exec ai-agent poetry run docai health${NC}"

echo -e "\n${BLUE}💡 Совет: Используйте --help с любой командой для получения подробной справки${NC}"