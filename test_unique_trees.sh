#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Тестирование уникальности деревьев решений ===${NC}"

# Создание тестовых запросов
echo -e "${YELLOW}Создание тестовых запросов...${NC}"

# Очистка старых файлов
rm -f /tmp/decision_trees_analysis/*.json 2>/dev/null || true

# Создание директории для тестов
mkdir -p /tmp/test_queries

# Создание тестовых файлов с разными запросами
cat > /tmp/test_queries/query1.txt << 'EOL'
Проверить соответствие договора поставки требованиям закона о госзакупках
EOL

cat > /tmp/test_queries/query2.txt << 'EOL'
Проверить соответствие трудового договора нормам трудового кодекса
EOL

cat > /tmp/test_queries/query3.txt << 'EOL'
Найти информацию о требованиях к оформлению документов
EOL

cat > /tmp/test_queries/query4.txt << 'EOL'
Какие документы нужны для регистрации ООО?
EOL

echo -e "${YELLOW}Выполнение тестовых запросов через AI агент...${NC}"

# Выполнение запросов
for i in {1..4}; do
    query=$(cat /tmp/test_queries/query${i}.txt)
    echo -e "${BLUE}Запрос ${i}: ${query}${NC}"
    
    # Выполнение запроса с визуализацией
    echo "$query" | docker-compose exec -T ai-agent poetry run python -m ai_agent.main query --web-visualization
    
    echo -e "${YELLOW}Пауза 2 секунды между запросами...${NC}"
    sleep 2
done

echo -e "${YELLOW}Анализ созданных файлов деревьев решений...${NC}"

# Проверка созданных файлов
if [ -d "/tmp/decision_trees_analysis" ]; then
    echo -e "${GREEN}Найдены файлы деревьев решений:${NC}"
    ls -la /tmp/decision_trees_analysis/*.json 2>/dev/null || echo -e "${RED}Файлы не найдены${NC}"
    
    # Подсчет уникальных файлов
    file_count=$(ls /tmp/decision_trees_analysis/*.json 2>/dev/null | wc -l)
    echo -e "${BLUE}Всего файлов: ${file_count}${NC}"
    
    if [ $file_count -gt 0 ]; then
        echo -e "${YELLOW}Сравнение содержимого файлов...${NC}"
        
        # Проверка уникальности содержимого
        unique_content=$(find /tmp/decision_trees_analysis -name "*.json" -exec md5sum {} \; | cut -d' ' -f1 | sort | uniq | wc -l)
        echo -e "${BLUE}Уникальных по содержимому: ${unique_content}${NC}"
        
        if [ $unique_content -eq $file_count ]; then
            echo -e "${GREEN}✓ Все файлы уникальны по содержимому!${NC}"
        else
            echo -e "${RED}✗ Найдены дублирующиеся файлы${NC}"
            echo -e "${YELLOW}MD5 хеши файлов:${NC}"
            find /tmp/decision_trees_analysis -name "*.json" -exec md5sum {} \;
        fi
        
        # Показать различия в первых строках файлов
        echo -e "${YELLOW}Первые строки каждого файла (для проверки различий):${NC}"
        for file in /tmp/decision_trees_analysis/*.json; do
            if [ -f "$file" ]; then
                echo -e "${BLUE}$(basename "$file"):${NC}"
                head -5 "$file" | grep -E '"id"|"query_text"|"timestamp"' || echo "Не найдены ключевые поля"
                echo "---"
            fi
        done
    fi
else
    echo -e "${RED}Директория /tmp/decision_trees_analysis не найдена${NC}"
fi

# Очистка тестовых файлов
rm -rf /tmp/test_queries

echo -e "\n${GREEN}=== Тестирование завершено ===${NC}"
echo -e "Для просмотра визуализации откройте: ${BLUE}http://localhost:8501${NC}"