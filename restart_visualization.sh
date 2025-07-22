#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Перезапуск системы визуализации деревьев решений ===${NC}"

# Остановка контейнера визуализации
echo -e "${YELLOW}Остановка контейнера визуализации...${NC}"
docker-compose stop decision-tree-viz

# Пересборка контейнера
echo -e "${YELLOW}Пересборка контейнера с исправленным Dockerfile...${NC}"
docker-compose build --no-cache decision-tree-viz

# Запуск контейнера
echo -e "${YELLOW}Запуск контейнера визуализации...${NC}"
docker-compose up -d decision-tree-viz

# Проверка статуса
echo -e "${YELLOW}Проверка статуса контейнера...${NC}"
docker-compose ps decision-tree-viz

echo -e "\n${GREEN}=== Контейнер визуализации перезапущен ===${NC}"
echo -e "Веб-интерфейс должен быть доступен по адресу: ${BLUE}http://10.50.50.10:8501${NC}"
echo -e "Проверьте логи контейнера: ${YELLOW}docker-compose logs -f decision-tree-viz${NC}"