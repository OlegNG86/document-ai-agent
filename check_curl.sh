#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Проверка доступности сервиса через curl ===${NC}"

# Установка curl, если не установлен
if ! command -v curl &> /dev/null; then
    echo -e "${YELLOW}Установка curl...${NC}"
    apt-get update && apt-get install -y curl
else
    echo -e "${GREEN}curl уже установлен${NC}"
fi

# Проверка доступности через localhost
echo -e "\n${YELLOW}Проверка localhost:8501...${NC}"
curl -v http://localhost:8501

# Проверка доступности через 0.0.0.0
echo -e "\n${YELLOW}Проверка 0.0.0.0:8501...${NC}"
curl -v http://0.0.0.0:8501

# Проверка доступности через IP
echo -e "\n${YELLOW}Проверка 10.50.50.10:8501...${NC}"
curl -v http://10.50.50.10:8501

# Проверка доступности через Nginx
echo -e "\n${YELLOW}Проверка 10.50.50.10 (Nginx)...${NC}"
curl -v http://10.50.50.10

# Проверка открытых портов
echo -e "\n${YELLOW}Открытые порты:${NC}"
netstat -tulpn | grep -E '8501|80'

# Проверка статуса контейнера
echo -e "\n${YELLOW}Статус контейнера:${NC}"
docker ps | grep ai-agent-visualization

echo -e "\n${GREEN}=== Проверка завершена ===${NC}"