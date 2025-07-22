#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Полное пересоздание контейнера визуализации ===${NC}"

# Остановка всех контейнеров
echo -e "${YELLOW}Остановка всех контейнеров...${NC}"
docker-compose down

# Удаление старого контейнера и образа
echo -e "${YELLOW}Удаление старого контейнера и образа...${NC}"
docker rm -f ai-agent-visualization 2>/dev/null || true
docker rmi document-ai-agent-v3_decision-tree-viz 2>/dev/null || true

# Очистка томов
echo -e "${YELLOW}Очистка томов...${NC}"
rm -rf visualization/data/decision_trees/*
mkdir -p visualization/data/decision_trees

# Пересборка контейнера
echo -e "${YELLOW}Пересборка контейнера с исправленным Dockerfile...${NC}"
docker-compose build --no-cache decision-tree-viz

# Запуск всех контейнеров
echo -e "${YELLOW}Запуск всех контейнеров...${NC}"
docker-compose up -d

# Проверка статуса
echo -e "${YELLOW}Проверка статуса контейнеров...${NC}"
docker-compose ps

echo -e "\n${GREEN}=== Контейнеры перезапущены ===${NC}"
echo -e "Веб-интерфейс должен быть доступен по адресу: ${BLUE}http://10.50.50.10:8501${NC}"
echo -e "Проверьте логи контейнера: ${YELLOW}docker-compose logs -f decision-tree-viz${NC}"