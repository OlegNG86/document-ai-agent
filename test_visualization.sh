#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Тестирование сервиса визуализации ===${NC}"

# Проверка статуса контейнера
echo -e "${YELLOW}Проверка статуса контейнера визуализации...${NC}"
if docker ps | grep -q "ai-agent-visualization"; then
    echo -e "${GREEN}✓ Контейнер ai-agent-visualization запущен${NC}"
else
    echo -e "${RED}✗ Контейнер ai-agent-visualization не найден${NC}"
    exit 1
fi

# Проверка логов контейнера
echo -e "${YELLOW}Последние логи контейнера:${NC}"
docker logs --tail 10 ai-agent-visualization

# Проверка доступности порта
echo -e "${YELLOW}Проверка доступности порта 8501...${NC}"
if curl -s -I http://localhost:8501 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Сервис доступен по адресу http://localhost:8501${NC}"
else
    echo -e "${RED}✗ Сервис недоступен по адресу http://localhost:8501${NC}"
    echo -e "${YELLOW}Попробуйте подождать несколько секунд и повторить тест${NC}"
fi

# Проверка наличия директории с данными
echo -e "${YELLOW}Проверка директории с данными деревьев решений...${NC}"
if docker exec ai-agent-visualization ls -la /app/data/decision_trees > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Директория /app/data/decision_trees доступна${NC}"
    docker exec ai-agent-visualization ls -la /app/data/decision_trees
else
    echo -e "${RED}✗ Директория /app/data/decision_trees недоступна${NC}"
fi

echo -e "\n${BLUE}=== Тестирование завершено ===${NC}"