#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Настройка Nginx для проксирования Streamlit ===${NC}"

# Проверка наличия Nginx
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}Установка Nginx...${NC}"
    apt-get update && apt-get install -y nginx
else
    echo -e "${GREEN}Nginx уже установлен${NC}"
fi

# Создание конфигурации Nginx
echo -e "${YELLOW}Создание конфигурации Nginx...${NC}"
cat > /etc/nginx/sites-available/streamlit << 'EOL'
server {
    listen 80;
    server_name 10.50.50.10;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
}
EOL

# Активация конфигурации
echo -e "${YELLOW}Активация конфигурации...${NC}"
ln -sf /etc/nginx/sites-available/streamlit /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

# Проверка конфигурации
echo -e "${YELLOW}Проверка конфигурации Nginx...${NC}"
nginx -t

# Перезапуск Nginx
echo -e "${YELLOW}Перезапуск Nginx...${NC}"
systemctl restart nginx

# Проверка статуса
echo -e "${YELLOW}Проверка статуса Nginx...${NC}"
systemctl status nginx --no-pager

echo -e "\n${GREEN}=== Настройка Nginx завершена ===${NC}"
echo -e "Веб-интерфейс должен быть доступен по адресу: ${BLUE}http://10.50.50.10/${NC}"
echo -e "Также доступен напрямую: ${BLUE}http://10.50.50.10:8501${NC}"