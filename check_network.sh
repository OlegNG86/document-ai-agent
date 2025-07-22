#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Проверка сетевых настроек ===${NC}"

# Проверка IP адресов
echo -e "${YELLOW}IP адреса:${NC}"
ip addr show

# Проверка маршрутов
echo -e "\n${YELLOW}Маршруты:${NC}"
ip route

# Проверка открытых портов
echo -e "\n${YELLOW}Открытые порты:${NC}"
netstat -tulpn

# Проверка Docker сети
echo -e "\n${YELLOW}Docker сети:${NC}"
docker network ls

# Проверка Docker контейнеров
echo -e "\n${YELLOW}Docker контейнеры:${NC}"
docker ps -a

# Проверка Nginx
echo -e "\n${YELLOW}Статус Nginx:${NC}"
systemctl status nginx --no-pager

# Проверка конфигурации Nginx
echo -e "\n${YELLOW}Конфигурация Nginx:${NC}"
cat /etc/nginx/sites-enabled/streamlit

echo -e "\n${GREEN}=== Проверка завершена ===${NC}"
echo -e "Если сервис недоступен, попробуйте следующие команды:"
echo -e "${YELLOW}1. ./start_minimal.sh${NC} - запустить минимальную версию"
echo -e "${YELLOW}2. ./setup_nginx.sh${NC} - настроить Nginx"
echo -e "${YELLOW}3. ./check_curl.sh${NC} - проверить доступность через curl"