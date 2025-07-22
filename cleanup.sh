#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Очистка репозитория от отладочных файлов ===${NC}"

# Удаление отладочных скриптов
echo -e "${YELLOW}Удаление отладочных скриптов...${NC}"
rm -f check_curl.sh check_network.sh check_service.sh fix_container.sh restart_visualization.sh start_minimal.sh start_simple.sh start_visualization.sh

# Удаление временных Docker файлов
echo -e "${YELLOW}Удаление временных Docker файлов...${NC}"
rm -f visualization/Dockerfile.fixed visualization/Dockerfile.simple visualization/Dockerfile.minimal

# Удаление временных docker-compose файлов
echo -e "${YELLOW}Удаление временных docker-compose файлов...${NC}"
rm -f docker-compose.simple.yml docker-compose.minimal.yml

# Удаление документации, созданной во время отладки
echo -e "${YELLOW}Удаление временной документации...${NC}"
rm -f VISUALIZATION_FIX.md FINAL_SOLUTION.md VISUALIZATION_SETUP.md

echo -e "\n${GREEN}=== Репозиторий очищен ===${NC}"