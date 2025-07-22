#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Проверка доступности сервиса визуализации ===${NC}"

# Проверка статуса контейнера
echo -e "${YELLOW}Статус контейнера:${NC}"
docker ps | grep ai-agent-visualization

# Проверка открытых портов
echo -e "\n${YELLOW}Открытые порты:${NC}"
netstat -tulpn | grep 8501

# Проверка доступности сервиса
echo -e "\n${YELLOW}Проверка доступности через curl:${NC}"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501
echo " <- Код ответа от localhost:8501"

curl -s -o /dev/null -w "%{http_code}" http://0.0.0.0:8501
echo " <- Код ответа от 0.0.0.0:8501"

curl -s -o /dev/null -w "%{http_code}" http://10.50.50.10:8501
echo " <- Код ответа от 10.50.50.10:8501"

# Проверка логов
echo -e "\n${YELLOW}Последние логи контейнера:${NC}"
docker logs --tail 20 ai-agent-visualization

echo -e "\n${GREEN}=== Проверка завершена ===${NC}"
echo -e "Если сервис недоступен, попробуйте следующие команды:"
echo -e "${YELLOW}1. docker-compose down${NC} - остановить все контейнеры"
echo -e "${YELLOW}2. docker-compose up -d${NC} - запустить все контейнеры заново"
echo -e "${YELLOW}3. ./restart_visualization.sh${NC} - перезапустить только контейнер визуализации"