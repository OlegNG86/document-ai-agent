#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Запуск минимальной версии системы визуализации ===${NC}"

# Остановка всех контейнеров
echo -e "${YELLOW}Остановка всех контейнеров...${NC}"
docker-compose down

# Удаление старого контейнера и образа
echo -e "${YELLOW}Удаление старого контейнера и образа...${NC}"
docker rm -f ai-agent-visualization 2>/dev/null || true
docker rmi document-ai-agent-v3_decision-tree-viz 2>/dev/null || true

# Создание минимального docker-compose файла
echo -e "${YELLOW}Создание минимального docker-compose файла...${NC}"
cat > docker-compose.minimal.yml << 'EOL'
version: "3.8"

services:
  # Minimal Streamlit visualization service
  streamlit:
    build:
      context: ./visualization
      dockerfile: Dockerfile.minimal
    container_name: ai-agent-visualization
    ports:
      - "0.0.0.0:8501:8501"
    environment:
      - STREAMLIT_SERVER_ADDRESS=0.0.0.0
      - STREAMLIT_SERVER_PORT=8501
    restart: unless-stopped
EOL

# Запуск с минимальным docker-compose файлом
echo -e "${YELLOW}Запуск с минимальным docker-compose файлом...${NC}"
docker-compose -f docker-compose.minimal.yml up -d

# Проверка статуса
echo -e "${YELLOW}Проверка статуса контейнеров...${NC}"
docker-compose -f docker-compose.minimal.yml ps

echo -e "\n${GREEN}=== Минимальная версия запущена ===${NC}"
echo -e "Веб-интерфейс должен быть доступен по адресу: ${BLUE}http://10.50.50.10:8501${NC}"
echo -e "Также через Nginx: ${BLUE}http://10.50.50.10/${NC}"
echo -e "Проверьте логи контейнера: ${YELLOW}docker-compose -f docker-compose.minimal.yml logs -f streamlit${NC}"